import sys
import time
from dd.bdd import BDD
import pnml_parser

class BDDSolver:
    def __init__(self, net: pnml_parser.PetriNet):
        self.net = net
        self.bdd = BDD()
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
            for p in pre:
                parts.append(f"{p}")
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
            t_logic = f"({' & '.join(parts)})"
            trans_exprs.append(t_logic)
        full_expr = " | ".join(trans_exprs)
        return full_expr

    def compute_reachable(self):
        print(f"Parsing complete. Net: {len(self.net.places)} places, {len(self.net.transitions)} transitions.")
        print("Constructing Symbolic Reachability Graph using BDDs...")        
        start_time = time.time()        
        m0_expr = self.build_initial_marking_expr()
        R_curr = self.bdd.add_expr(m0_expr)
        tr_expr = self.build_transition_relation_expr()
        Trans_Rel = self.bdd.add_expr(tr_expr)       
        iterations = 0
        while True:
            iterations += 1
            rel_and_curr = self.bdd.apply('and', R_curr, Trans_Rel)
            next_states_prime = self.bdd.exist(self.vars, rel_and_curr)
            next_states = self.bdd.rename(next_states_prime, self.rename_map)
            R_new = self.bdd.apply('or', R_curr, next_states)
            if R_new == R_curr:
                break           
            R_curr = R_new            
        end_time = time.time()
        count = self.bdd.count(R_curr, nvars=len(self.vars))       
        print(f"\n--- Task 3 Results ---")
        print(f"Total reachable markings: {count}")
        print(f"Iterations: {iterations}")
        print(f"Time: {end_time - start_time:.6f}s")       
        return R_curr

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pnml_file>")
        sys.exit(1)    
    try:
        net = pnml_parser.parse_pnml(sys.argv[1])
        solver = BDDSolver(net)
        solver.compute_reachable()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()