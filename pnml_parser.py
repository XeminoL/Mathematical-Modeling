import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List

class PNMLParserError(Exception):
    """Error while parsing PNML or validating the Petri net."""
    pass

@dataclass
class Place:
    id: str
    name: str | None = None
    initial_marking: int = 0

@dataclass
class Transition:
    id: str
    name: str | None = None

@dataclass
class Arc:
    id: str
    source: str
    target: str

class PetriNet:
    def __init__(
        self,
        places: Dict[str, Place],
        transitions: Dict[str, Transition],
        arcs: List[Arc],
    ):
        self.places = places
        self.transitions = transitions
        self.arcs = arcs

    def validate(self) -> None:
        errors: List[str] = []

        if not self.places:
            errors.append("The net has no places.")
        if not self.transitions:
            errors.append("The net has no transitions.")

        node_types: Dict[str, str] = {}

        for pid in self.places:
            if pid in node_types:
                errors.append(f"Duplicate id between place and transition: {pid}")
            node_types[pid] = "place"

        for tid in self.transitions:
            if tid in node_types:
                errors.append(f"Duplicate id between place and transition: {tid}")
            node_types[tid] = "transition"

        for arc in self.arcs:
            s_type = node_types.get(arc.source)
            t_type = node_types.get(arc.target)

            if s_type is None:
                errors.append(
                    f"Arc {arc.id} refers to non-existing source node '{arc.source}'."
                )
            if t_type is None:
                errors.append(
                    f"Arc {arc.id} refers to non-existing target node '{arc.target}'."
                )
            if s_type is not None and t_type is not None and s_type == t_type:
                errors.append(
                    f"Arc {arc.id} connects two {s_type}s "
                    f"({arc.source} -> {arc.target}), which is not valid in a Petri net."
                )

        if errors:
            raise PNMLParserError("\n".join(errors))

    def print_summary(self) -> None:
        print("Petri net parsed successfully!")
        print(f"Number of places      : {len(self.places)}")
        print(f"Number of transitions : {len(self.transitions)}")
        print(f"Number of arcs        : {len(self.arcs)}")
        print()

        print("Places:")
        for p in self.places.values():
            print(
                f"  - {p.id:10s} | name={p.name!r} | initial_marking={p.initial_marking}"
            )
        print()

        print("Transitions:")
        for t in self.transitions.values():
            print(f"  - {t.id:10s} | name={t.name!r}")
        print()

        print("Arcs:")
        for a in self.arcs:
            print(f"  - {a.id:10s} : {a.source} -> {a.target}")

def _strip_ns(tag: str) -> str:
    """Strip XML namespace from a tag, e.g. '{ns}place' -> 'place'."""
    return tag.split("}", 1)[-1] if "}" in tag else tag

def parse_pnml(path: str) -> PetriNet:
    """Parse a PNML file and return a PetriNet object."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise PNMLParserError(f"Invalid PNML file: {e}") from e
    except FileNotFoundError:
        raise PNMLParserError(f"File not found: {path}")

    root = tree.getroot()

    places: Dict[str, Place] = {}
    transitions: Dict[str, Transition] = {}
    arcs: List[Arc] = []

    for elem in root.iter():
        tag = _strip_ns(elem.tag)

        if tag == "place":
            pid = elem.attrib.get("id")
            if pid is None:
                raise PNMLParserError("A place is missing the 'id' attribute.")

            if pid in places:
                raise PNMLParserError(f"Duplicate place id: {pid}")

            name = None
            initial_marking = 0

            for child in elem:
                ctag = _strip_ns(child.tag)
                if ctag == "name":
                    text_elem = next(
                        (c for c in child if _strip_ns(c.tag) == "text"), None
                    )
                    if text_elem is not None and text_elem.text is not None:
                        name = text_elem.text.strip()
                elif ctag == "initialMarking":
                    text_elem = next(
                        (c for c in child if _strip_ns(c.tag) == "text"), None
                    )
                    if text_elem is not None and text_elem.text is not None:
                        text = text_elem.text.strip()
                        try:
                            initial_marking = int(text)
                        except ValueError:
                            raise PNMLParserError(
                                f"initialMarking of place {pid} is not an integer: {text!r}"
                            )

            places[pid] = Place(id=pid, name=name, initial_marking=initial_marking)

        elif tag == "transition":
            tid = elem.attrib.get("id")
            if tid is None:
                raise PNMLParserError("A transition is missing the 'id' attribute.")

            if tid in transitions:
                raise PNMLParserError(f"Duplicate transition id: {tid}")

            name = None
            for child in elem:
                ctag = _strip_ns(child.tag)
                if ctag == "name":
                    text_elem = next(
                        (c for c in child if _strip_ns(c.tag) == "text"), None
                    )
                    if text_elem is not None and text_elem.text is not None:
                        name = text_elem.text.strip()

            transitions[tid] = Transition(id=tid, name=name)

        elif tag == "arc":
            aid = elem.attrib.get("id")
            source = elem.attrib.get("source")
            target = elem.attrib.get("target")

            if aid is None or source is None or target is None:
                raise PNMLParserError(
                    "An arc is missing one of the attributes: id / source / target."
                )

            arcs.append(Arc(id=aid, source=source, target=target))

    net = PetriNet(places, transitions, arcs)
    net.validate()
    return net

def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print(f"  python {sys.argv[0]} <path_to_pnml_file>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        net = parse_pnml(path)
    except PNMLParserError as e:
        print("ERROR while reading PNML:")
        print(e)
        sys.exit(1)

    net.print_summary()

if __name__ == "__main__":
    main()
