from scipy.optimize import linprog

# Coefficients for the objective function (maximize x, so minimize -x)
c = [0, 0, 0, 0, -1]  # -x (we minimize -x to maximize x)

# Coefficients for the inequality constraints
A_ub = [
    [1, -1,  0,  0, -1],  # A - B >= x -> A - B - x >= 0
    [0,  1, -1,  0, -1],  # B - C >= x -> B - C - x >= 0
    [0,  0,  1, -1, -1],  # C - D >= x -> C - D - x >= 0
    [-1, 1,  0,  0,  0],  # A >= B -> -A + B <= 0
    [0, -1, 1,  0,  0],   # B >= C -> -B + C <= 0
    [0,  0, -1, 1,  0]    # C >= D -> -C + D <= 0
]

b_ub = [0, 0, 0, 0, 0, 0]  # Right-hand side of the inequalities

# Coefficients for the equality constraint
A_eq = [[1, 1, 1, 1, 0]]  # A + B + C + D = 100
b_eq = [100]  # Right-hand side of the equality

# Bounds for the variables (A, B, C, D, x)
bounds = [(0, None),  # A >= 0
          (0, None),  # B >= 0
          (0, None),  # C >= 0
          (0, None),  # D >= 0
          (0, None)]  # x >= 0

# Solve the linear program
result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

# Print the results
if result.success:
    A, B, C, D, x = result.x  # Ensure x is the last variable
    print(f"Maximum minimum difference: {x}")
    print(f"A = {A}, B = {B}, C = {C}, D = {D}")
else:
    print("No solution found.")
