# %%
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp
from collections import namedtuple
from graphviz import Digraph


Task = namedtuple('Task', ['successor', 'predecessor'])
tasks = {x: Task(successor=[], predecessor=[]) for x in range(1, 11)}

precedence_graph = [
(1, 2),
(1, 3),
(2, 5),
(3, 6),
(4, 6),
(5, 7),
(5, 8),
(6, 8),
(6, 9),
(7, 10),
(9, 10),
]

def precedence(precedence_graph: list):
    """
    fill the successor and predecessor information of the tasks with the given precedence graph. Precedence graph information as list with tuples for precedence, e.g.
    1->2, 1->3 is [(1, 2), (1, 3)]

    Args:
        precedence_graph (list): precedence graph with in this format [(1, 2), (1, 4)]
    """
    j = 1
    precedence = {}
    successor = []
    for prec in precedence_graph:
        p1, p2 = prec
        if p1 not in precedence.keys():
            precedence[p1] = []
        precedence[p1].append(p2)
        tasks[p1].successor.append(p2)
        tasks[p2].predecessor.append(p1)
        j += 1

precedence(precedence_graph)

# %%
def plot_graph():
    dot = Digraph()
    for task in tasks:
        dot.node(str(task), str(task))

    for task_number, info in tasks.items():
        for successor_ in info.successor:
            dot.edge(str(task_number), str(successor_))

    return dot

plot_graph()
# %%

def all_predecessors(task_number: int) -> np.array:
    """
    recursively search the precedence graph for all predecessors of a given task number

    Args:
        task_number (int): task number from which all predecessors should be determined

    Returns:
        np.array: array with all predecessor task numbers
    """
    precedence_list = []
    def find_all_prec(task_number, precedence_list):
        if tasks[task_number].predecessor:
            precedence_list.extend(tasks[task_number].predecessor)
            for predecessor_ in tasks[task_number].predecessor:
                find_all_prec(predecessor_, precedence_list)
    find_all_prec(task_number, precedence_list)
    return np.array(list(set(precedence_list)))

all_prec = all_predecessors(9)
all_prec

# %%
E1 = [8, 13, 49, 15, 18, 15, 10, 10, 33, 25]
E2 = [6, None, 40, None, 14, 12, 8, 8, None, 20]
E3 = [None, 14, None, 17, None, 20, None, 13, 38, 28]
num_equipments = 3
num_tasks = 10
num_stations = num_tasks
cost = [100_000, 100_000, 60_000]
df = pd.DataFrame({'E1': E1, 'E2': E2, 'E3': E3})

x_ijk = np.zeros((num_tasks, num_equipments, num_stations), dtype=object)
y_jk = np.zeros((num_equipments, num_stations), dtype=object)

# %%
solver = pywraplp.Solver('balancing_robots_bukchin', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
solver.Clear()

# create variables
for i in range(x_ijk.shape[0]):
    for j in range(x_ijk.shape[1]):
        for k in range(x_ijk.shape[2]):
            x_ijk[i][j][k] = solver.BoolVar(name=f"x_{i}{j}{k}")

for j in range(y_jk.shape[0]):
    for k in range(y_jk.shape[1]):
        y_jk[j][k] = solver.BoolVar(name=f"y_{j}{k}")


print('Number of variables:', solver.NumVariables())
# %%

# create objective function
# (1) represents the total design cost to be minimized
solver.Minimize(solver.Sum(
    [cost[j] * y_jk[j, :].sum() for j in range(num_equipments)]
))

# %%
def multiply_with_index(array: np.array):
    return np.arange(1, array.size + 1) @ array.transpose()


def one_hot_bool(array: np.array, row_length: int) -> np.array:
    """
    return a one-hot encoded boolean array of shape (row_length, )
    array specifies the indices of the one-hot values
    e.g. np.array([0, 1, 3]), row_length = 4:
        array([1., 1., 0., 1.])

    Args:
        array (np.array): index array
        row_length (int): row length

    Returns:
        np.array: one-hot encoded bool array of shape (row_length, )
    """
    assert row_length >= array.size
    one_hot = np.zeros(row_length, dtype=bool)
    # convert from precedence graph based counting starting at 1 to array based starting at 0
    one_hot[array - 1] = True
    return one_hot

# create constraints
# (2) ensures that if task g is an immediate predecessor of task h, then it cannot be assigned to a station with a higher index than the station to which task h is assigned.
# [x] implemented
for task in tasks:
    task_precedence = all_predecessors(task)
    if task_precedence.any():
        one_hot_task_precedence = one_hot_bool(task_precedence, num_tasks)
        for x_jk in x_ijk[one_hot_task_precedence]:
            sum_k_xgjk = np.sum(np.apply_along_axis(multiply_with_index, 1, x_jk))
            sum_l_xhjl = np.sum(np.apply_along_axis(multiply_with_index, 1, x_ijk[task - 1]))
            solver.Add(sum_k_xgjk <= sum_l_xhjl)

print('Number of constraints:', solver.NumConstraints())

# %%
# test_ijk = np.arange(num_tasks * num_equipments * num_stations).reshape(num_tasks, num_equipments, num_stations)
# test_jk = np.arange(3 * num_tasks).reshape(3, num_tasks)

# test = np.apply_along_axis(multiply_with_index, 1, test_jk)
# test


# %%
# (3) ensures that each task is performed exactly once
# [x] implemented
for i in range(x_ijk.shape[0]):
    solver.Add(x_ijk[i].sum() == 1)

# (4) represents the relationship between the x_ijk and the y_jk variables by not allowing any task to be performed on a given piece of equipment in a given station, if this equipment is not assigned to that station.
# [ ] implemented


# (5) represents the requirement of at most one piece of equipment at any station
# [x] implemented
for k in range(y_jk.shape[1]):
    solver.Add(y_jk[:, k].sum() <= 1)


# %%
result_status = solver.Solve()
# The problem has an optimal solution.
# assert result_status == pywraplp.Solver.OPTIMAL

# The solution looks legit (when using solvers others than
# GLOP_LINEAR_PROGRAMMING, verifying the solution is highly recommended!).
assert solver.VerifySolution(1e-4, True)

print('Solution:')
print('Number of robots:', sum([x_ijk[i].solution_value() for i in range(len(x_ijk))]))

price = 0
footprint = 0
handling = 0
separation = 0
joining = 0
robots = []
print('-' * 65)
for i in range(len(df)):
    if x_ijk[i].solution_value() > 0:
        c = df.loc[df.name == str(x_ijk[i]), 'price'].values[0]
        s = df.loc[df.name == str(x_ijk[i]), 'footprint'].values[0]
        handling += df.loc[df.name == str(x_ijk[i]), 'operation_handling'].values[0] * x_ijk[i].solution_value()
        separation += df.loc[df.name == str(x_ijk[i]), 'operation_separation'].values[0] * x_ijk[i].solution_value()
        joining += df.loc[df.name == str(x_ijk[i]), 'operation_joining'].values[0] * x_ijk[i].solution_value()
        robots.append(str(x_ijk[i]))
        print('{:<10} | num: {:<5} | price: {:<5.2f} € | footprint: {:<5} m2'.format(str(x_ijk[i]), x_ijk[i].solution_value(), c, s))
        price += c
        footprint += s

print('-' * 65)
print('Price =', price, '€')
print('Footprint =', round(footprint, 3), 'm2')
print('Handling =', handling, '/', constraints['handling'])
print('Separation =', separation, '/', constraints['separation'])
print('Joining =', joining, '/', constraints['joining'])


# **Objective here is to minimize the fitness function**

# df.loc[df.name.isin(robots), :]
