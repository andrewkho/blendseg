import aabb_tree

class AABBDirectionalTree (aabb_tree.AABBTree):
    def __init__(self, mesh, direction):
        self._dirn = direction

        faces = list(mesh.faces.values())
        """ Perform a sort by minimum index """
        sorted_faces = sorted(faces, key=lambda face: face.min[self._dirn])

        self._tree = AABBDirectionalNode(sorted_faces, self._dirn)

class AABBDirectionalNode (aabb_tree.AABBNode):
    """ A node of an Axis-aligned bounding box tree. """

    def __init__(self, faces, forced_direction):
        """ Initialize this node.

        Pass a list of faces, and two points representing the AABB
        of all those faces.
        
        Find longest axis of the AABB and split points along the halfway point
        into two new nodes, left and right.
        """
        if len(faces) is 1:
            self.leaf = faces[0]
            self.left_node = None
            self.right_node = None
            self.max_pt = faces[0].max
            self.min_pt = faces[0].min
            return

        self.min_pt = [0,0,0]
        self.max_pt = [0,0,0]

        maxi = forced_direction

        sorted_faces = faces
        self.faces = sorted_faces
        split_index = len(sorted_faces)//2
        left_sorted_faces = sorted_faces[:split_index]
        right_sorted_faces = sorted_faces[split_index:]

        """ Create left and right children """
        self.left_node = AABBDirectionalNode(left_sorted_faces, forced_direction)
        self.right_node = AABBDirectionalNode(right_sorted_faces, forced_direction)
        
        """ Now update my bounding box """
        for i in range(0,3):
            if (self.left_node.min_pt[i] < self.right_node.min_pt[i]):
                self.min_pt[i] = self.left_node.min_pt[i]
            else:
                self.min_pt[i] = self.right_node.min_pt[i]
            if (self.left_node.max_pt[i] > self.right_node.max_pt[i]):
                self.max_pt[i] = self.left_node.max_pt[i]
            else:
                self.max_pt[i] = self.right_node.max_pt[i]

