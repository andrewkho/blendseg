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
        sysmin = sys.float_info.min
        sysmax = sys.float_info.max
        
        self.max = [sysmin, sysmin, sysmin]
        self.min = [sysmax, sysmax, sysmax]

        for v in mesh.getVerts().values():
            if v[0] < self.min[0]:
                self.min[0] = v[0]
            elif v[0] > self.max[0]:
                self.max[0] = v[0]
            if v[1] < self.min[1]:
                self.min[1] = v[1]
            elif v[1] > self.max[1]:
                self.max[1] = v[1]
            if v[2] < self.min[2]:
                self.min[2] = v[2]
            elif v[2] > self.max[2]:
                self.max[2] = v[2]
        """ Construct the tree """
        self._tree = AABBNode(list(mesh.faces.values()), self.max, self.min)

class AABBNode (object):
    """ A node of an Axis-aligned bounding box tree. """

    def __init__(self, faces, max_pt, min_pt):
        """ Initialize this node.

        Pass a list of faces, and two points representing the AABB
        of all those faces.
        
        Find longest axis of the AABB and split points along the halfway point
        into two new nodes, left and right.
        """

        if len(faces) is 1:
            self.leaf = faces[0]
            return
        
        self.max_pt = max_pt
        self.min_pt = min_pt
        
        maxd = 0
        maxi = -1
        for i in range(0,2):
            d = max_pt[i] - min_pt[i]
            if d > maxd:
                maxd = d
                maxi = i

        """ Sort faces based on minimum point in maxi dimension """
        sorted_faces, pts = self.quicksort_max_min(faces, maxi)
        split_index = len(sorted_faces)//2
        left_sorted_faces = sorted_faces[:split_index]
        right_sorted_faces = sorted_faces[split_index:]

        left_max_pt = pts[0]
        right_max_pt = pts[1]
        left_min_pt = pts[2]
        right_min_pt = pts[3]
        # sysmin = sys.float_info.min
        # sysmax = sys.float_info.max
        
        # left_max_pt = [sysmin, sysmin, sysmin]
        # left_min_pt = [sysmax, sysmax, sysmax]
        # right_max_pt = [sysmin, sysmin, sysmin]
        # right_min_pt = [sysmax, sysmax, sysmax]

        # for face in left_sorted_faces:
        #     left_max_pt[0] = max(left_max_pt[0], face.max[0])
        #     left_max_pt[1] = max(left_max_pt[1], face.max[1])
        #     left_max_pt[2] = max(left_max_pt[2], face.max[2])
        #     left_min_pt[0] = min(left_min_pt[0], face.min[0])
        #     left_min_pt[1] = min(left_min_pt[1], face.min[1])
        #     left_min_pt[2] = min(left_min_pt[2], face.min[2])

        # for face in right_sorted_faces:
        #     right_max_pt[0] = max(right_max_pt[0], face.max[0])
        #     right_max_pt[1] = max(right_max_pt[1], face.max[1])
        #     right_max_pt[2] = max(right_max_pt[2], face.max[2])
        #     right_min_pt[0] = min(right_min_pt[0], face.min[0])
        #     right_min_pt[1] = min(right_min_pt[1], face.min[1])
        #     right_min_pt[2] = min(right_min_pt[2], face.min[2])

        self.left_node = AABBNode(left_sorted_faces, left_max_pt, left_min_pt)
        self.right_node = AABBNode(right_sorted_faces, right_max_pt, right_min_pt)

    def quicksort(self, faces, dim):
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

    def quicksort_max_min(self, faces, dim):
        """ Quicksort algorithm applied to a list of faces.
        Sort along dimension (0, 1, or 2) by minimum value of BB.

        Also calculates max/min points.
        """
        
        if (len(faces) <= 1):
            return faces,[]
        
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
                left_max_pt[0] = max(left_max_pt[0], face.max[0])
                left_max_pt[1] = max(left_max_pt[1], face.max[1])
                left_max_pt[2] = max(left_max_pt[2], face.max[2])
                left_min_pt[0] = min(left_min_pt[0], face.min[0])
                left_min_pt[1] = min(left_min_pt[1], face.min[1])
                left_min_pt[2] = min(left_min_pt[2], face.min[2])
            else:
                greater.append(face)
                right_max_pt[0] = max(right_max_pt[0], face.max[0])
                right_max_pt[1] = max(right_max_pt[1], face.max[1])
                right_max_pt[2] = max(right_max_pt[2], face.max[2])
                right_min_pt[0] = min(right_min_pt[0], face.min[0])
                right_min_pt[1] = min(right_min_pt[1], face.min[1])
                right_min_pt[2] = min(right_min_pt[2], face.min[2])

        res = self.quicksort(less,dim)
        res.append(pivot)
        res.extend(self.quicksort(greater,dim))
        
        return res, [left_max_pt, right_max_pt, left_min_pt, right_min_pt]

