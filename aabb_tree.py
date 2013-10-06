import sys
from operator import itemgetter

import object_intersection
from time import time

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
        return self._tree.collides_with_tree(other_tree._tree)

    def update_bbs(self):
        """ Update this tree's AABB's. This will result
        in a higher degree of overlap.

        TODO: In order for this to work, face max/min must be updated
        first. This means vertices need to be tracked. """
        self._tree.update_bbs()

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
        
        # """ First compute BB for this set of faces """
        sysmin = sys.float_info.min
        sysmax = sys.float_info.max
        self.min_pt = [sysmax, sysmax, sysmax]
        self.max_pt = [sysmin, sysmin, sysmin]
        
        """ It's actually faster to sort 3 times and use
        as an ESTIMATE of the max/min than to iterate through
        all faces. """
        maxd = 0
        maxi = -1

        fs = [None, None, None]
        # faces.sort(key=lambda face:face.min[0])
        fs[0] = sorted(faces, key=lambda face:face.min[0])
        d = faces[-1].max[0] - faces[0].min[0]
        if d > maxd:
            maxd = d
            maxi = 0
        # faces.sort(key=lambda face:face.min[1])
        fs[1] = sorted(faces, key=lambda face:face.min[1])
        d = faces[-1].max[1] - faces[0].min[1]
        if d > maxd:
            maxd = d
            maxi = 1
        # faces.sort(key=lambda face:face.min[2])
        fs[2] = sorted(faces, key=lambda face:face.min[2])
        d = faces[-1].max[2] - faces[0].min[2]
        if d > maxd:
            maxd = d
            maxi = 2

        """ Sort according to minimum index. It is faster
        to do in-place sort because faces might already be sorted
        in this direction. """
        # faces.sort(key=lambda face:face.min[maxi])
        # sorted_faces = faces
        sorted_faces = fs[maxi]
        
        split_index = len(sorted_faces)//2
        left_sorted_faces = sorted_faces[:split_index]
        right_sorted_faces = sorted_faces[split_index:]

        self.left_node = AABBNode(left_sorted_faces)
        self.right_node = AABBNode(right_sorted_faces)


        self.min_pt[0] = min(self.left_node.min_pt[0],
                             self.right_node.min_pt[0])
        self.min_pt[1] = min(self.left_node.min_pt[1],
                             self.right_node.min_pt[1])
        self.min_pt[2] = min(self.left_node.min_pt[2],
                             self.right_node.min_pt[2])
        self.max_pt[0] = max(self.left_node.max_pt[0],
                             self.right_node.max_pt[0])
        self.max_pt[1] = max(self.left_node.max_pt[1],
                             self.right_node.max_pt[1])
        self.max_pt[2] = max(self.left_node.max_pt[2],
                             self.right_node.max_pt[2])
        # for i in range(0,3):
        #     self.min_pt[i] = min(self.left_node.min_pt[i],
        #                       self.right_node.min_pt[i])
        #     self.max_pt[i] = max(self.left_node.max_pt[i],
        #                       self.right_node.max_pt[i])

    def is_leaf(self):
        return self.left_node is None and self.right_node is None

    def collides_with(self, pt_max, pt_min):
        if (self.min_pt[0] > pt_max[0] or self.max_pt[0] < pt_min[0]): 
            return False
        if (self.min_pt[1] > pt_max[1] or self.max_pt[1] < pt_min[1]): 
            return False
        if (self.min_pt[2] > pt_max[2] or self.max_pt[2] < pt_min[2]): 
            return False
            
        if (self.left_node == None and self.right_node == None):
            return True
        
        return (self.left_node.collides_with(pt_max, pt_min) or
                self.right_node.collides_with(pt_max, pt_min))

    def collides_with_tree(self, other_tree):
        if (self.min_pt[0] > other_tree.max_pt[0] or
            self.max_pt[0] < other_tree.min_pt[0]): 
            return []
        if (self.min_pt[1] > other_tree.max_pt[1] or
            self.max_pt[1] < other_tree.min_pt[1]): 
            return []
        if (self.min_pt[2] > other_tree.max_pt[2] or
            self.max_pt[2] < other_tree.min_pt[2]): 
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

    def update_bbs(self):
        """ Recursively update this bounding box and recurisvely call
        on children. """

        if self.is_leaf():
            self.max_pt = self.leaf.max
            self.min_pt = self.leaf.min
            return

        self.left_node.update_bbs()
        self.right_node.update_bbs()

        self.min_pt[0] = min(self.left_node.min_pt[0],
                             self.right_node.min_pt[0])
        self.min_pt[1] = min(self.left_node.min_pt[1],
                             self.right_node.min_pt[1])
        self.min_pt[2] = min(self.left_node.min_pt[2],
                             self.right_node.min_pt[2])
        self.max_pt[0] = max(self.left_node.max_pt[0],
                             self.right_node.max_pt[0])
        self.max_pt[1] = max(self.left_node.max_pt[1],
                             self.right_node.max_pt[1])
        self.max_pt[2] = max(self.left_node.max_pt[2],
                             self.right_node.max_pt[2])

        # for i in range(0,3):
        #     self.min_pt[i] = min(self.left_node.min_pt[i],
        #                          self.right_node.min_pt[i])
        #     self.max_pt[i] = max(self.left_node.max_pt[i],
        #                          self.right_node.max_pt[i])

