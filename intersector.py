from copy import deepcopy

# mathutils is a blender package... This should maybe be moved
from mathutils.geometry import intersect_ray_tri

from .quad_edge_mesh import quad_edge_mesh
from .quad_edge_mesh import aabb_tree

class Intersector (object):
    def __init__(self):
        self._saved_results = {}

    def clear_saved_results(self):
        self._saved_results = {}
    
    def compute_intersection_contour(self, mesh1, mesh2, tree1, tree2):
        """ Compute the intersection contour of mesh1 and mesh2.
        mesh1, mesh2 must be of type QEMesh.
        tree1, tree2 must be of type AABBTree.
        """

        if type(mesh1) is not quad_edge_mesh.QEMesh:
            raise TypeError("mesh1 must be of type QEMesh!")
        if type(mesh2) is not quad_edge_mesh.QEMesh:
            raise TypeError("mesh2 must be of type QEMesh!")
        if type(tree1) is not aabb_tree.AABBTree:
            raise TypeError("tree1 must be of type AABBTree!")
        if type(tree2) is not aabb_tree.AABBTree:
            raise TypeError("tree2 must be of type AABBTree!")


        ix_points = []
        pairs = tree1.collides_with_tree(tree2)

        for pair in pairs:
            new_ixpoints = self._intersect_faces(pair[0], pair[1])
            ix_points.extend(new_ixpoints)

    def _get_norm_squared(self, vector):
        return (vector[0]*vector[0] +
                vector[1]*vector[1] +
                vector[2]*vector[2])

    def _intersect_faces(self, face1, face2):
        """ compute intersection of two QEFace objects.
        Return a list of IntersectionPoints.
        """
        ix_points = []
        for edge in face1.edges:
            point = self._intersect_edge_face(edge, face2)
            if point is not None:
                ix_points.append(point)
        for edge in face2.edges:
            point = self._intersect_edge_face(edge, face1)
            if point is not None:
                ix_points.append(point)

        return ix_points

    def _intersect_edge_face(self, edge, face):
        """ Compute intersection for one edge and one face.
        Returns None if no intersection occured, and a IntersectionPoint
        if one is found.
        """
        if (edge, face) in self._saved_results:
            return self._saved_results[(edge, face)]
        
        direction = deepcopy(edge.t_vert.pos)
        direction[0] = direction[0] - edge.b_vert.pos[0]
        direction[1] = direction[1] - edge.b_vert.pos[1]
        direction[2] = direction[2] - edge.b_vert.pos[2]

        point = intersect_ray_tri(face.verts[0], face.verts[1], face.verts[2],
                          edge.b_vert.pos, direction)

        if not point:
            ix_point = None

        elif self._get_norm_squared(point) > self._get_norm_squared(direction):
            ix_point = None
        else:
            ix_point = IntersectionPoint(edge, face, point)
            
        self._saved_results[(edge, face)] = ix_point

        return ix_point

class IntersectionPoint (object):
    """ Store intersection information between a QEEdge and a QEFace.
    edge is QEEdge.
    face is QEFace.
    Point is stored as a 3-list of floats.
    """
    def __init__(self, edge, face, point):
        self.edge = edge
        self.face = face
        self.point = point
