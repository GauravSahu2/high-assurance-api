---- MODULE TransferLogic ----
EXTENDS Integers
VARIABLES balanceA, balanceB
Init == balanceA = 100 /\ balanceB = 0
Next == balanceA >= 50 /\ balanceA' = balanceA - 50 /\ balanceB' = balanceB + 50
Invariant == balanceA >= 0 /\ balanceB >= 0
====
