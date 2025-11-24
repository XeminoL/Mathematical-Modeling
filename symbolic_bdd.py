import sys
import time
from dd.bdd import BDD
import pnml_parser

class BDDSolver:
    def __init__(self, net: pnml_parser.PetriNet):
        self.net = net
        self.bdd = BDD()
        
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
        
        full_expr = " & ".join(expr_parts)
        return self.bdd.add_expr(full_expr)

    def encode_transition_relation(self):
        full_relation = self.bdd.false
        
        for t_id in self.net.transitions:
            pre = self.preset[t_id]
            post = self.postset[t_id]
            
            t_expr_parts = []
            for p in pre:
                t_expr_parts.append(f"{p}")
            
            for p_id in self.net.places:
                p_curr = p_id
                p_next = f"{p_id}_prime"
                
                if p_id in pre and p_id not in post:
                    t_expr_parts.append(f"~{p_next}")
                elif p_id in post and p_id not in pre:
                    t_expr_parts.append(f"{p_next}")
                elif p_id in pre and p_id in post:
                    t_expr_parts.append(f"{p_next}")
                else:
                    t_expr_parts.append(f"({p_curr} <-> {p_next})")
            
            t_bdd = self.bdd.add_expr(" & ".join(t_expr_parts))
            full_relation = full_relation | t_bdd
            
        return full_relation

    def compute_reachable(self):
        start_time = time.time()
        
        R_curr = self.encode_initial_marking()
        Trans_Rel = self.encode_transition_relation()
        
        iterations = 0
        while True:
            iterations += 1
            rel_and_curr = R_curr & Trans_Rel
            
            next_states_prime = self.bdd.exist(self.vars, rel_and_curr)
            next_states = self.bdd.let(self.rename_map, next_states_prime)
            
            R_new = R_curr | next_states
            
            if R_new == R_curr:
                break
            
            R_curr = R_new
            
        end_time = time.time()
        count = self.bdd.count(R_curr, nvars=len(self.vars))
        
        print(f"\n--- Task 3 (Symbolic BDD) Results ---")
        print(f"Total reachable markings: {count}")
        print(f"Iterations: {iterations}")
        print(f"Time taken: {end_time - start_time:.6f} seconds")
        return R_curr

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pnml_file>")
        sys.exit(1)
        
    net = pnml_parser.parse_pnml(sys.argv[1])
    solver = BDDSolver(net)
    solver.compute_reachable()

if __name__ == "__main__":
    main()