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
        self.clear_saved_results()

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

        ix_contours = self._create_intersection_contours(ix_points)

        return ix_contours

    def _create_intersection_contours(self, ix_points):
        """ Return a list of intersection contours.
        Each contour is an ordered list of IntersectionPoints.

        Closed contours will have the same start and end points.
        Open contours are also possible.
        """
        contours = []
        while len(ix_points) != 0:
            contour = self._get_one_contour(ix_points)
            contours.append(contour)
            
    def _get_one_contour(self, ix_points):
        """ From a list of IntersectionPoints, construct a contour
        by walking around. Removes IntersectionPoints from ix_points.
        Returns a list of IntersectionPoints representing the contour.

        A closed contour's first and last points are the same.
        """
        if len(ix_points) == 0:
            return None

        # A break condition if contour isn't closed
        contour_is_open = False
        first_ixp = ixp = ix_points[0]
        next_ixp = None
        contour = list(ixp)
        prev_face = ixp.r_face
        while next_ixp is not contour[0]:
            next_ixp = None
            # First search this edge's-face's edges for intersection with ixp.face
            if ixp.edge.r_face is prev_face:
                this_edges_face = ixp.edge.l_face
            else:
                this_edges_face = ixp.edge.r_face

            if this_edges_face is None:
                # We seem to have found the edge of a mesh. Continue from first ixp in
                # in opposite direction unless we already did once
                if contour_is_open:
                    # We already found one end of this open contour.
                    # Now we've found the other so we're done
                    break
                next_ixp = first_ixp
                contour.reverse()
                prev_face = first_ixp.l_face
                ixp = next_ixp
                ix_points.remove(ixp)
                contour_is_open = True
                continue
                
            for cand_edge in this_edges_face.edges:
                if cand_edge is ixp.edge:
                    continue
                # if this candidate-edge crosses this edge's face, it's x-point is the next point
                if (cand_edge, ixp.face) in self._saved_results:
                    next_ixp = self._saved_results[(cand_edge, ixp.face)]
                    prev_face = this_edges_face
                    break
            
            if next_ixp is None:
                # We didn't find it so the next xpoint must be on other face
                for cand_edge in ixp.face.edges:
                    if (cand_edge, this_edges_face) in self._saved_results:
                        next_ixp = self._saved_results[(cand_edge, this_edges_face)]
                        prev_face = ixp.face
                        break

            ixp = next_ixp
            ix_points.remove(ixp)
            contour.append(ixp)

        return contour
        

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
