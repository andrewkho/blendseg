import sys

import object_intersection
import imp
imp.reload(object_intersection)

class AABBTree (object):
    """ An Axis-aligned bounding box tree.
    For speedy intersection queries!
    """

    def __init__(self, mesh):
        """ Construct an AABB Tree for this mesh.
        Mesh must be of type object_intersection.CMesh
        """
                
        """ Construct the tree """
        self._tree = AABBNode(list(mesh.faces.values()))

    def collides_with(self, other_face):
        """ Search tree for collision """
        pt_max = other_face.max
        pt_min = other_face.min
        return self._tree.collides_with(pt_max, pt_min)

    def collides_with_tree(self, other_tree):
        """ Return a list of pairs of faces whose aabb's collide """
        pairs = list()

        pairs = self._tree.collides_with_tree(other_tree._tree)

        return pairs
        

class AABBNode (object):
    """ A node of an Axis-aligned bounding box tree. """

    def __init__(self, faces):
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

        """ First compute BB for this set of faces """
        sysmin = sys.float_info.min
        sysmax = sys.float_info.max
        self.min_pt = [sysmax, sysmax, sysmax]
        self.max_pt = [sysmin, sysmin, sysmin]
        
        for face in faces:
            self.min_pt[0] = min(self.min_pt[0],face.min[0])
            self.min_pt[1] = min(self.min_pt[1],face.min[1])
            self.min_pt[2] = min(self.min_pt[2],face.min[2])
            self.max_pt[0] = max(self.max_pt[0],face.max[0])
            self.max_pt[1] = max(self.max_pt[1],face.max[1])
            self.max_pt[2] = max(self.max_pt[2],face.max[2])

        maxd = 0
        maxi = -1
        for i in range(0,3):
            d = self.max_pt[i] - self.min_pt[i]
            if d > maxd:
                maxd = d
                maxi = i
        
        """ Sort faces based on minimum point in maxi dimension """
        sorted_faces = self.quicksort(faces, maxi)
        split_index = len(sorted_faces)//2
        left_sorted_faces = sorted_faces[:split_index]
        right_sorted_faces = sorted_faces[split_index:]

        self.left_node = AABBNode(left_sorted_faces)
        self.right_node = AABBNode(right_sorted_faces)

    def is_leaf(self):
        return self.left_node is None and self.right_node is None

    def collides_with(self, pt_max, pt_min):
        for i in range(0,3):
            if (self.min_pt[i] > pt_max[i] or self.max_pt[i] < pt_min[i]): 
                return False
            
        if (self.left_node == None and self.right_node == None):
            return True
        
        return (self.left_node.collides_with(pt_max, pt_min) or
                self.right_node.collides_with(pt_max, pt_min))

    def collides_with_tree(self, other_tree):
        for i in range(0,3):
            if (self.min_pt[i] > other_tree.max_pt[i] or
                self.max_pt[i] < other_tree.min_pt[i]): 
                return []

        if self.is_leaf():
            if other_tree.is_leaf():
                return [(self.leaf, other_tree.leaf)]
            else:
                return self.collides_with_tree(other_tree.left_node) + \
                    self.collides_with_tree(other_tree.right_node)
        elif other_tree.is_leaf():
            return self.left_node.collides_with_tree(other_tree) + \
                self.right_node.collides_with_tree(other_tree)
        else:
            return self.left_node.collides_with_tree(other_tree.left_node) + \
                self.left_node.collides_with_tree(other_tree.right_node) + \
                self.right_node.collides_with_tree(other_tree.left_node) + \
                self.right_node.collides_with_tree(other_tree.right_node)
        
    def quicksort(self, faces, dim):
        """ Quicksort algorithm applied to a list of faces.
        Sort along dimension (0, 1, or 2) by minimum value of BB.
        """

        if (len(faces) <= 1):
            return faces
        
        less = list()
        greater = list()
        pivot = faces[len(faces)//2]
        faces.remove(pivot)
        
        sysmin = sys.float_info.min
        sysmax = sys.float_info.max

        left_max_pt = [sysmin, sysmin, sysmin]
        left_min_pt = [sysmax, sysmax, sysmax]
        right_max_pt = [sysmin, sysmin, sysmin]
        right_min_pt = [sysmax, sysmax, sysmax]

        for face in faces:
            if face.min[dim] < pivot.min[dim]:
                less.append(face)
            else:
                greater.append(face)

        res = self.quicksort(less,dim)
        res.append(pivot)
        res.extend(self.quicksort(greater,dim))
        
        return res
