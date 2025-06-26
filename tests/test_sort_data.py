from cdb import sort_data
import pytest


@pytest.mark.parametrize(
    "input_data,expected",
    [
        ([], []),
        ([(1, 2, 3)], [(1, 2, 3)]),
        ([(3, 2, 1), (1, 2, 3), (1, 1, 5)], [(1, 1, 5), (1, 2, 3), (3, 2, 1)]),
        ([(5, 5, 5), (5, 5, 3), (5, 5, 1)], [(5, 5, 5), (5, 5, 3), (5, 5, 1)]),
        ([(2, 3, 4), (2, 1, 5), (1, 3, 6)], [(1, 3, 6), (2, 1, 5), (2, 3, 4)]),
        (
            [(100, 0, 0), (0, 100, 0), (0, 0, 100)],
            [(0, 0, 100), (0, 100, 0), (100, 0, 0)],
        ),
    ],
)
def test_sort_data(input_data, expected):
    assert sort_data(input_data) == expected


def test_sort_stability():
    input_data = [(1, 1, 1), (1, 1, 2), (1, 1, 3)]
    assert sort_data(input_data) == input_data


def test_large_input():
    input_data = [(i % 100, (i + 1) % 100, i) for i in range(1000, 0, -1)]
    sorted_data = sort_data(input_data)
    for i in range(len(sorted_data) - 1):
        assert (sorted_data[i][0], sorted_data[i][1]) <= (
            sorted_data[i + 1][0],
            sorted_data[i + 1][1],
        )


@pytest.mark.parametrize(
    "input_data",
    [
        [(2**64, 0, 0)],
        [(-(2**63), 2**63 - 1, 0)],
        [(0, 0, 0), (0, 0, 1), (0, 0, 2**64 - 1)],
    ],
)
def test_extreme_values(input_data):
    assert len(sort_data(input_data)) == len(input_data)
