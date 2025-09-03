from .fitness import assign_penalty


def test_assign_penalty_value_equals_nominal():
    assert assign_penalty(10, 10, 1, 1, 100, 10) == 0

def test_assign_penalty_value_shallow_gradient_used_within_tolerance():
    # Value is half way between nominal and min so penalty = 0.5 * 2
    assert assign_penalty(35, 50, 2, 20, 70, 10) == 1
    
    # Value is half way between nominal and max so penalty = 0.5 * 2
    assert assign_penalty(60, 50, 2, 20, 70, 10) == 1

def test_assign_penalty_value_steep_gradient_used_outside_tolerance():
    # Penalty of 2 at the min plus 500 * (0.20 - 0.10) below min = 5002
    assert assign_penalty(10, 50, 2, 20, 80, 500) == 5002
    # Penalty of 2 at the max plus 500 * (100 - 80) after max = 10002
    assert assign_penalty(100, 50, 2, 20, 80, 500) == 10002


