import sys
import time
import pulp
from dd.bdd import BDD
import pnml_parser

class HybridSolver:
    def __init__(self, net: pnml_parser.PetriNet):
        self.net = net
        self.bdd = BDD()
        self.bdd.configure(reordering=True)
        
        self.vars = []
        self.next_vars = [] 
        self.rename_map = {} 
        
        for p_id in net.places:
            curr_var = p_id
            next_var = f"{p_id}_prime"
            self.bdd.declare(curr_var)
            self.bdd.declare(next_var)
            self.vars.append(curr_var)
            self.next_vars.append(next_var)
            self.rename_map[next_var] = curr_var

        self.preset = {t: set() for t in net.transitions}
        self.postset = {t: set() for t in net.transitions}
        self._build_structure()
        
        self.reachable_bdd = None

    def _build_structure(self):
        for arc in self.net.arcs:
            if arc.source in self.net.places and arc.target in self.net.transitions:
                self.preset[arc.target].add(arc.source)
            elif arc.source in self.net.transitions and arc.target in self.net.places:
                self.postset[arc.source].add(arc.target)

    def encode_initial_marking(self):
        expr_parts = []
        for p_id, place in self.net.places.items():
            if place.initial_marking > 0:
                expr_parts.append(f"{p_id}")
            else:
                expr_parts.append(f"~{p_id}")
        return self.bdd.add_expr(" & ".join(expr_parts))

    def encode_transition_relation(self):
        full_relation = self.bdd.false
        for t_id in self.net.transitions:
            pre = self.preset[t_id]
            post = self.postset[t_id]
            t_expr_parts = []
            for p in pre: 
                t_expr_parts.append(f"{p}")
            for p_id in self.net.places:
                p_curr, p_next = p_id, f"{p_id}_prime"
                if p_id in pre and p_id not in post: 
                    t_expr_parts.append(f"~{p_next}")
                elif p_id in post and p_id not in pre: 
                    t_expr_parts.append(f"{p_next}")
                elif p_id in pre and p_id in post: 
                    t_expr_parts.append(f"{p_next}")
                else: 
                    t_expr_parts.append(f"({p_curr} <-> {p_next})")
            full_relation = full_relation | self.bdd.add_expr(" & ".join(t_expr_parts))
        return full_relation

    def compute_reachable_set(self):
        start = time.time()
        R = self.encode_initial_marking()
        T = self.encode_transition_relation()
        while True:
            next_s = self.bdd.let(self.rename_map, self.bdd.exist(self.vars, R & T))
            R_new = R | next_s
            if R_new == R: 
                break
            R = R_new
        self.reachable_bdd = R
        print(f"Reachable set computed in {time.time() - start:.4f}s. Size: {self.bdd.count(R, len(self.vars))}")

    def find_deadlock(self):
        if self.reachable_bdd is None:
            self.compute_reachable_set()

        print("\n--- Starting Hybrid Deadlock Detection ---")
        start_time = time.time()
        
        prob = pulp.LpProblem("Deadlock_Finder", pulp.LpMinimize)
        ilp_vars = {p: pulp.LpVariable(f"x_{p}", cat='Binary') for p in self.net.places}

        for t_id, pre_places in self.preset.items():
            if not pre_places: 
                continue
            prob += pulp.lpSum([ilp_vars[p] for p in pre_places]) <= len(pre_places) - 1, f"Disable_{t_id}"

        attempts = 0
        while True:
            attempts += 1
            status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
            
            if status != pulp.LpStatusOptimal:
                print("ILP Infeasible: NO DEADLOCK.")
                break

            candidate_marking = {}
            bdd_expr_parts = []
            
            for p_id in self.net.places:
                val = int(pulp.value(ilp_vars[p_id]) or 0)
                candidate_marking[p_id] = val
                if val == 1:
                    bdd_expr_parts.append(f"{p_id}")
                else:
                    bdd_expr_parts.append(f"~{p_id}")
            
            candidate_bdd_expr = " & ".join(bdd_expr_parts)
            candidate_node = self.bdd.add_expr(candidate_bdd_expr)

            if (candidate_node & self.reachable_bdd) != self.bdd.false:
                print(f"DEADLOCK FOUND at attempt {attempts}!")
                print(f"Marking: {candidate_marking}")
                print(f"Time taken: {time.time() - start_time:.4f}s")
                return candidate_marking
            else:
                ones = [ilp_vars[p] for p, v in candidate_marking.items() if v == 1]
                zeros = [ilp_vars[p] for p, v in candidate_marking.items() if v == 0]
                prob += (pulp.lpSum(ones) - pulp.lpSum(zeros)) <= len(ones) - 1, f"Cut_{attempts}"

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pnml_file>")
        sys.exit(1)
        
    net = pnml_parser.parse_pnml(sys.argv[1])
    solver = HybridSolver(net)
    solver.find_deadlock()

if __name__ == "__main__":
    main()