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
        self.sorted_places = sorted(net.places.keys())
        self.vars = []
        self.next_vars = [] 
        self.rename_map = {} 
        for p_id in self.sorted_places:
            curr_var = p_id
            next_var = f"{p_id}_p" 
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

    def build_initial_marking_expr(self):
        expr_parts = []
        for p_id in self.vars:
            place = self.net.places[p_id]
            if place.initial_marking > 0:
                expr_parts.append(f"{p_id}")
            else:
                expr_parts.append(f"!{p_id}")
        return " & ".join(expr_parts)

    def build_transition_relation_expr(self):
        trans_exprs = []
        for t_id in self.net.transitions:
            pre = self.preset[t_id]
            post = self.postset[t_id]
            parts = []
            for p in pre: parts.append(f"{p}")
            for p_curr in self.vars:
                p_next = f"{p_curr}_p"
                if p_curr in pre and p_curr not in post:
                    parts.append(f"!{p_next}")
                elif p_curr in post and p_curr not in pre:
                    parts.append(f"{p_next}")
                elif p_curr in pre and p_curr in post:
                    parts.append(f"{p_next}")
                else:
                    parts.append(f"(({p_curr} & {p_next}) | (!{p_curr} & !{p_next}))")           
            trans_exprs.append(f"({' & '.join(parts)})")       
        return " | ".join(trans_exprs)

    def compute_reachable_set(self):
        start = time.time()
        m0_expr = self.build_initial_marking_expr()
        tr_expr = self.build_transition_relation_expr()
        R = self.bdd.add_expr(m0_expr)
        T = self.bdd.add_expr(tr_expr)    
        iterations = 0
        while True:
            iterations += 1
            rel_and_curr = self.bdd.apply('and', R, T)
            next_s_prime = self.bdd.exist(self.vars, rel_and_curr)
            next_s = self.bdd.rename(next_s_prime, self.rename_map)           
            R_new = self.bdd.apply('or', R, next_s)           
            if R_new == R: 
                break
            R = R_new         
        self.reachable_bdd = R
        count = self.bdd.count(R, len(self.vars))
        print(f"Reachable set computed in {time.time() - start:.4f}s. Size: {count}")
        return count

    def find_deadlock(self):
        if self.reachable_bdd is None:
            self.compute_reachable_set()
        print("\n--- Task 4 Results ---")
        start_time = time.time()
        prob = pulp.LpProblem("Deadlock_Finder", pulp.LpMaximize)
        ilp_vars = {p: pulp.LpVariable(f"x_{p}", cat='Binary') for p in self.net.places}
        prob += pulp.lpSum(ilp_vars.values()), "Maximize_Tokens"
        for t_id, pre_places in self.preset.items():
            if not pre_places: continue
            prob += pulp.lpSum([ilp_vars[p] for p in pre_places]) <= len(pre_places) - 1, f"Disable_{t_id}"
        attempts = 0
        while True:
            attempts += 1
            status = prob.solve(pulp.PULP_CBC_CMD(msg=0))  
            if status != pulp.LpStatusOptimal:
                print("ILP Infeasible: No dead marking exists.")
                print("Status: NO DEADLOCK found.")
                break
            candidate_marking = {}
            bdd_expr_parts = []
            for p_id in self.vars:
                val = int(pulp.value(ilp_vars[p_id]) or 0)
                candidate_marking[p_id] = val
                if val == 1:
                    bdd_expr_parts.append(f"{p_id}")
                else:
                    bdd_expr_parts.append(f"!{p_id}")          
            candidate_bdd_expr = " & ".join(bdd_expr_parts)
            candidate_node = self.bdd.add_expr(candidate_bdd_expr)
            intersection = self.bdd.apply('and', candidate_node, self.reachable_bdd)            
            if intersection != self.bdd.false:
                print(f"DEADLOCK FOUND at attempt {attempts}!")
                dead_places = [p for p, v in candidate_marking.items() if v == 1]
                print(f"Deadlock Marking: {dead_places}")
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
    try:
        net = pnml_parser.parse_pnml(sys.argv[1])
        solver = HybridSolver(net)
        solver.find_deadlock()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()