import sys
import collections
import time

try:
    import pnml_parser
except ImportError:
    print("Error: Could not find 'pnml_parser.py'.")
    print("Make sure it's in the same directory as this script.")
    sys.exit(1)

def convert_net_to_bfs_format(net: pnml_parser.PetriNet):
    initial_marking_set = {
        p.id for p in net.places.values() if p.initial_marking > 0
    }
    transitions_dict = {}
    for t_id in net.transitions.keys():
        transitions_dict[t_id] = {'pre': set(), 'post': set()}      
    for arc in net.arcs:
        source_id = arc.source
        target_id = arc.target
        if source_id in net.places and target_id in net.transitions:
            transitions_dict[target_id]['pre'].add(source_id)
        elif source_id in net.transitions and target_id in net.places:
            transitions_dict[source_id]['post'].add(target_id)           
    return initial_marking_set, transitions_dict

def find_reachable_markings_bfs(start_marking, all_transitions):
    initial_state = frozenset(start_marking)   
    visited = set()
    queue = collections.deque()   
    visited.add(initial_state)
    queue.append(initial_state)   
    while queue:
        current_marking = queue.popleft()       
        for t_id, t_info in all_transitions.items():          
            pre_set = t_info['pre']
            post_set = t_info['post']
            if pre_set.issubset(current_marking):
                temp_marking = current_marking - pre_set
                next_marking_set = temp_marking | post_set
                next_marking = frozenset(next_marking_set)
                if next_marking not in visited:
                    visited.add(next_marking)
                    queue.append(next_marking)
    return visited

def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print(f"  python {sys.argv[0]} <path_to_pnml_file>")
        sys.exit(1)        
    pnml_file_path = sys.argv[1]   
    print(f"Parsing PNML file: {pnml_file_path}...")
    try:
        parsed_net = pnml_parser.parse_pnml(pnml_file_path)
    except pnml_parser.PNMLParserError as e:
        print(f"ERROR during parsing:\n{e}")
        sys.exit(1)    
    print("Parsing complete.")  
    start_marking_set, transitions_dict = convert_net_to_bfs_format(parsed_net)
    print("Starting BFS to find reachable markings...")
    start_time = time.time()
    reachable_set = find_reachable_markings_bfs(start_marking_set, transitions_dict)   
    end_time = time.time()
    duration = end_time - start_time 
    print(f"\n--- Task 2 Results ---")
    print(f"Total reachable markings found: {len(reachable_set)}")
    print(f"Time taken: {duration:.6f} seconds")
    print("All Reachable Markings:")   
    for i, marking_fs in enumerate(reachable_set):
        marking = set(marking_fs)
        print(f"  {i+1}: {marking or '∅'}")

if __name__ == "__main__":
    main()