import tkinter as tk
from tkinter import simpledialog, messagebox
import random
from graph.GraphUtils import Graph
import math

class GraphGUI:
    def __init__(self, master):
        self.graph = Graph(is_directed=True)
        self.master = master
        master.title("Graph Creator")

        self.canvas = tk.Canvas(master, width=500, height=400, bg="white")
        self.canvas.pack()

        self.add_node_btn = tk.Button(master, text="Add Node", command=self.add_node)
        self.add_node_btn.pack()

        self.add_edge_btn = tk.Button(master, text="Add Edge", command=self.add_edge)
        self.add_edge_btn.pack()

        self.show_matrix_btn = tk.Button(master, text="Show Matrix", command=self.show_matrix)
        self.show_matrix_btn.pack()

        self.generate_matrix_btn = tk.Button(master, text="Generate Matrix", command=self.copy_matrix_to_clipboard)
        self.generate_matrix_btn.pack()

        # Button to generate and show weights dictionary
        self.generate_weights_btn = tk.Button(master, text="Show Weights Dict", command=self.copy_weights_to_clipboard)
        self.generate_weights_btn.pack()

        self.node_positions = {}
        # New: weights dictionary
        self.weights = {}

    def add_node(self):
        node = simpledialog.askstring("Input", "Node label:")
        if node and node not in self.graph.nodes():
            self.graph.add_node(node)
            # Place node at random position
            x = random.randint(50, 450)
            y = random.randint(50, 350)
            self.node_positions[node] = (x, y)
            self.draw_graph()

    def add_edge(self):
        node1 = simpledialog.askstring("Input", "Source node:")
        node2 = simpledialog.askstring("Input", "Target node:")
        if node1 and node2 and node1 in self.graph.nodes() and node2 in self.graph.nodes():
            weight_str = simpledialog.askstring("Input", f"Weight for edge {node1}->{node2} (float):")
            try:
                weight = float(weight_str)
            except (TypeError, ValueError):
                messagebox.showerror("Error", f"Invalid weight '{weight_str}'. Please enter a float.")
                return
            self.graph.add_edge(node1, node2)
            self.weights[(node1, node2)] = weight
            self.draw_graph()

    def show_matrix(self):
        try:
            nodes, matrix = self.graph.to_matrix()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compute matrix: {e}")
            return

        if not nodes:
            messagebox.showinfo("Adjacency Matrix", "Graph has no nodes.")
            return

        matrix_str = "Nodes: " + ", ".join(map(str, nodes)) + "\nMatrix:\n"
        for row in matrix:
            matrix_str += " ".join(map(str, row)) + "\n"
        messagebox.showinfo("Adjacency Matrix", matrix_str)

    def draw_graph(self):
        self.canvas.delete("all")
        r = 20  # node radius

        for node in self.graph.nodes():
            if node not in self.node_positions:
                x = random.randint(50, 450)
                y = random.randint(50, 350)
                self.node_positions[node] = (x, y)

        # Draw edges with arrows and weight labels
        adjacency = getattr(self.graph, "adjacency", {})
        for node1, neighbors in adjacency.items():
            x1, y1 = self.node_positions.get(node1, (0, 0))
            for node2 in neighbors:
                x2, y2 = self.node_positions.get(node2, (0, 0))
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy)
                if dist == 0:
                    continue
                offset_x = dx * r / dist
                offset_y = dy * r / dist
                start_x = x1 + offset_x
                start_y = y1 + offset_y
                end_x = x2 - offset_x
                end_y = y2 - offset_y
                self.canvas.create_line(
                    start_x, start_y, end_x, end_y, arrow=tk.LAST, width=2
                )
                # Draw weight label at the midpoint
                midpoint_x = (start_x + end_x) / 2
                midpoint_y = (start_y + end_y) / 2
                w = self.weights.get((node1, node2))
                if w is not None:
                    self.canvas.create_text(midpoint_x, midpoint_y - 10, text=str(w), font=("Arial", 10, "bold"), fill="darkred")

        for node, (x, y) in self.node_positions.items():
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="lightblue")
            self.canvas.create_text(x, y, text=node, font=("Arial", 12, "bold"))

    def matrix_literal(self, matrix, var_name="matrix", indent=4):
        if not matrix:
            return f"{var_name} = []"
        lines = [f"{var_name} = ["]
        for row in matrix:
            row_str = ", ".join(str(int(x)) for x in row)
            lines.append(" " * indent + f"[{row_str}],")
        lines[-1] = lines[-1].rstrip(",")
        lines.append("]")
        return "\n".join(lines)

    def copy_matrix_to_clipboard(self, var_name="matrix"):
        try:
            nodes, matrix = self.graph.to_matrix()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compute matrix: {e}")
            return

        nodes_literal = "nodes = [" + ", ".join(repr(n) for n in nodes) + "]\n"
        literal = self.matrix_literal(matrix, var_name=var_name, indent=4)
        full_text = nodes_literal + literal

        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(full_text)
        except Exception:
            pass

        win = tk.Toplevel(self.master)
        win.title("Copy-ready Matrix")
        txt = tk.Text(win, width=60, height=max(6, len(matrix) + 3), wrap="none")
        txt.pack(padx=10, pady=10)
        txt.insert("1.0", full_text)
        txt.focus_set()
        txt.tag_add("sel", "1.0", "end")
        btn_close = tk.Button(win, text="Close", command=win.destroy)
        btn_close.pack(pady=(0, 10))

    # NEW: Method to output weights dictionary
    def copy_weights_to_clipboard(self):
        # keys that are integers should have tuple keys as integers (if your node labels are integers)
        # otherwise, string keys will be used
        lines = ["weights = {"]
        for (u, v), w in self.weights.items():
            lines.append(f"    ({repr(u)}, {repr(v)}): {w},")
        lines[-1] = lines[-1].rstrip(",")
        lines.append("}")
        text = "\n".join(lines)

        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(text)
        except Exception:
            pass

        win = tk.Toplevel(self.master)
        win.title("Copy-ready Weights Dict")
        txt = tk.Text(win, width=60, height=max(6, len(self.weights) + 3), wrap="none")
        txt.pack(padx=10, pady=10)
        txt.insert("1.0", text)
        txt.focus_set()
        txt.tag_add("sel", "1.0", "end")
        btn_close = tk.Button(win, text="Close", command=win.destroy)
        btn_close.pack(pady=(0, 10))
