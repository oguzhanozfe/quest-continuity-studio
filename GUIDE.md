# Quest state review

Describe a quest as up to twelve named boolean flags, an initial set of flags, repeatable actions and goals. Actions list required and forbidden flags and the flags they set or clear. Goals use the same condition lists. The relay-chamber example includes two achievable objectives, a condition that already holds at the start and a goal requiring two flags that cannot coexist.

Breadth-first search explores each reachable flag configuration exactly once. Transitions have equal cost, so the first witness found for a goal uses the fewest actions. Action declaration order breaks ties. For impossible goals, the evidence includes one reachable state with the fewest unsatisfied conditions. This is diagnostic evidence, not a proposed rewrite of the story.

Approve individual proofs to export a JSON playthrough with before-and-after states for every step and a Graphviz DOT diagram. An already-satisfied goal has a valid zero-action proof. Reachability assumes the input contains every relevant prerequisite. Inventory counts, spatial restrictions and real-time timers need explicit modeling outside this boolean format.
