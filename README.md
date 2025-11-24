# Symbolic and Algebraic Reasoning in Petri Nets 
Petri nets are among the most fundamental and elegant mathematical models for describing concurrent, distributed, and event-driven systems [18, 15]. They provide a graphical and formal way to represent how conditions (places) and events (transitions) interact through the flow of tokens, enabling a precise analysis of system behavior. Since their introduction by Carl Adam Petri in the early 1960s [19], Petri nets have become a cornerstone of formal methods [3, 20], system verification [6, 20], workflow modeling [22, 21], and biological network analysis [4, 1].

From a theoretical perspective, Petri nets occupy a unique position at the intersection of graph theory, discrete dynamical systems, linear algebra, and logic-based reasoning [18, 15, 14, 3, 12]. Many core questions in computer science—such as reachability, liveness, and deadlock-freedom—can be formally stated and analyzed within the Petri net framework.

However, these problems are also computationally challenging: even for small systems, the state space explosion caused by concurrency can lead to an exponential number of reachable markings [15, 3].

From a practical perspective, Petri nets offer a bridge between modeling and computation [18]. They are used to design and analyze manufacturing systems [16], communication protocols [9], concurrent programs [8], and even biological regulatory networks [13]. In these applications, the ability to compute and analyze the reachability graph—a directed graph representing all possible system states and their transitions—is crucial for verifying correctness and discovering hidden behaviors such as deadlocks or unsafe states [15, 22].

To address the scalability challenge, symbolic representations such as Binary Decision Diagrams (BDDs) [2] have been introduced to compactly encode large state spaces. Meanwhile, Integer Linear Programming (ILP) [7] provides a flexible optimization-based framework to reason about properties of these state spaces. They have been separately applied to efficiently analyze Petri nets [17, 12]. Combining these two techniques has the potential to enable both efficient state-space exploration and formal property checking.

In this assignment, students shall build a small-scale application integrating this idea:
1. Use BDDs to symbolically construct the of reachable markings of a given 1-safe Petri net (see [5] for more details about 1-safe Petri nets).
2. Apply ILP formulations to detect deadlocks [15, 17] in combination with the resulting BDD.
