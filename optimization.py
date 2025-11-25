import sys
import time
import pulp
from dd.bdd import BDD
import pnml_parser

class OptimizationSolver:
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
        parts = []
        for p_id in self.vars:
            if self.net.places[p_id].initial_marking > 0: parts.append(p_id)
            else: parts.append(f"!{p_id}")
        return " & ".join(parts)

    def build_transition_relation_expr(self):
        trans_exprs = []
        for t_id in self.net.transitions:
            pre, post = self.preset[t_id], self.postset[t_id]
            parts = []
            for p in pre: parts.append(p)
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
        while True:
            rel_and_curr = self.bdd.apply('and', R, T)
            next_s_prime = self.bdd.exist(self.vars, rel_and_curr)
            next_s = self.bdd.rename(next_s_prime, self.rename_map)         
            R_new = self.bdd.apply('or', R, next_s)           
            if R_new == R: 
                break
            R = R_new
        self.reachable_bdd = R
        print(f"Reachable set computed in {time.time() - start:.4f}s. Size: {self.bdd.count(R, len(self.vars))}")

    def optimize_marking(self, weights: dict):
        if self.reachable_bdd is None:
            self.compute_reachable_set()
        print("\n--- Task 5 Results ---")
        print(f"Weights: {weights}")
        start_time = time.time()        
        prob = pulp.LpProblem("Optimization_Finder", pulp.LpMaximize)
        ilp_vars = {p: pulp.LpVariable(f"x_{p}", cat='Binary') for p in self.net.places}
        obj_func = []
        for p_id in self.net.places:
            w = weights.get(p_id, 0)
            obj_func.append(w * ilp_vars[p_id])      
        prob += pulp.lpSum(obj_func), "Objective_Value"
        attempts = 0
        while True:
            attempts += 1
            status = prob.solve(pulp.PULP_CBC_CMD(msg=0))          
            if status != pulp.LpStatusOptimal:
                print("ILP Infeasible: No more solutions found.")
                print("Optimization finished.")
                return None
            candidate_marking = {}
            bdd_expr_parts = []
            current_obj_value = pulp.value(prob.objective)           
            for p_id in self.vars:
                val_raw = pulp.value(ilp_vars[p_id])
                val = int(val_raw) if val_raw is not None else 0       
                candidate_marking[p_id] = val
                if val == 1:
                    bdd_expr_parts.append(f"{p_id}")
                else:
                    bdd_expr_parts.append(f"!{p_id}")
            candidate_bdd = self.bdd.add_expr(" & ".join(bdd_expr_parts))
            intersection = self.bdd.apply('and', candidate_bdd, self.reachable_bdd)
            if intersection != self.bdd.false:
                print(f"OPTIMAL MARKING FOUND at attempt {attempts}!")
                print(f"Marking: {candidate_marking}")
                print(f"Total Objective Value: {current_obj_value}")
                print(f"Time taken: {time.time() - start_time:.4f}s")
                return candidate_marking
            else:
                ones = [ilp_vars[p] for p, v in candidate_marking.items() if v == 1]
                zeros = [ilp_vars[p] for p, v in candidate_marking.items() if v == 0]
                prob += (pulp.lpSum(ones) - pulp.lpSum(zeros)) <= len(ones) - 1, f"Cut_{attempts}"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <pnml_file> [target_place_id]")
        sys.exit(1)  
    filename = sys.argv[1]
    try:
        net = pnml_parser.parse_pnml(filename)
        solver = OptimizationSolver(net)  
        weights = {}
        if len(sys.argv) > 2:
            target_place = sys.argv[2]
            if target_place in net.places:
                weights[target_place] = 100 
                print(f"Target optimization: Maximize tokens in '{target_place}'")
            else:
                print(f"Warning: Place '{target_place}' not found.")
                for p in net.places: weights[p] = 1
        else:
            print("Auto-assigning weights based on filename for testing...")
            if "choice" in filename:
                weights = {'p0': 1, 'p1': 10, 'p2': 20}
            elif "example" in filename:
                weights = {'p1': 5, 'p2': 10}
            elif "loop" in filename:
                weights = {'p_start': 10, 'p_mid': 5}
            else:
                for p in net.places: weights[p] = 1               
        solver.optimize_marking(weights)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()