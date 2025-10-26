import tkinter as tk
import sys

from graph.GraphGUI import GraphGUI
from graph.GraphUtils import Graph
from test.graphTemplates import example_dag, example_cyclic_aperiodic, example_periodic_failure


root = tk.Tk()
gui = GraphGUI(root)
root.mainloop()