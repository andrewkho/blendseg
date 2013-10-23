from copy import deepcopy
from time import time

# mathutils is a blender package... This should maybe be moved
from mathutils.geometry import intersect_ray_tri
from mathutils.geometry import intersect_line_plane
from mathutils import Vector

from .quad_edge_mesh.quad_edge_mesh import QEMesh
from .quad_edge_mesh.aabb_tree import AABBTree

from .slice_plane import SlicePlane

class Intersector (object):
    show_timing_msgs = False
    
    def __init__(self):
        self._saved_results = {}

    def clear_saved_results(self):
        self._saved_results = {}

    def compute_intersection_with_plane(self, mesh, tree, plane):
        """ Compute the intersection with a plane.
        Hopefully this optimization will speed things up dramatically.
        mesh is a QEMesh, tree is an AABBTree
        plane is a slice_plane
        """
        if not isinstance(mesh, QEMesh):
            raise TypeError("mesh must be of type QEMesh!")
        if not isinstance(tree, AABBTree):
            raise TypeError("tree must be of type AABBTree!")
        if not isinstance(plane, SlicePlane):
            raise TypeError("plane must be of type SlicePlane!")

        if Intersector.show_timing_msgs:
            print("    AABB Tree checking (with plane)")
            start = time()
        orientation = plane.orientation.__index__()
        pos_vec = plane.get_location()
        position = pos_vec[plane.orientation]
        faces = tree.collides_with_orthogonal_plane(orientation, position)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)

        if Intersector.show_timing_msgs:
            print("    Deep search for intersection (with plane)")
            start = time()
        ix_points = []
        for face in faces:
            new_ixpoints = self._intersect_face_plane(face, orientation, position)
            ix_points.extend(new_ixpoints)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)
        
        # print("found %d ixpoints" % len(self._saved_results))
        if Intersector.show_timing_msgs:
            print("    Constructing contour")
            start = time()
        ix_contours = self._create_intersection_contours(ix_points)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)
        
        return ix_contours
    
    def compute_intersection_contour(self, mesh1, mesh2, tree1, tree2):
        """ Compute the intersection contour of mesh1 and mesh2.
        mesh1, mesh2 must be of type QEMesh.
        tree1, tree2 must be of type AABBTree.
        """
        self.clear_saved_results()

        if not isinstance(mesh1, QEMesh):
            raise TypeError("mesh1 must be of type QEMesh!")
        if not isinstance(mesh2, QEMesh):
            raise TypeError("mesh2 must be of type QEMesh!")
        if not isinstance(tree1, AABBTree):
            raise TypeError("tree1 must be of type AABBTree!")
        if not isinstance(tree2, AABBTree):
            raise TypeError("tree2 must be of type AABBTree!")

        if Intersector.show_timing_msgs:
            print("    AABB Tree collision")
            start = time()
        pairs = tree1.collides_with_tree(tree2)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)

        if Intersector.show_timing_msgs:
            print("Searching %d pairs" % len(pairs))

        if Intersector.show_timing_msgs:
            print("    Deep search for intersections")
            start = time()
        ix_points = []
        for pair in pairs:
            new_ixpoints = self._intersect_faces(pair[0], pair[1])
            ix_points.extend(new_ixpoints)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)

        if Intersector.show_timing_msgs:
            print("found %d ixpoints" % len(self._saved_results))
            print("    Constructing contour")
            start = time()
        ix_contours = self._create_intersection_contours(ix_points)
        if Intersector.show_timing_msgs:
            seconds = time() - start
            print("    Took %1.5f seconds" % seconds)

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

        return contours
            
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
        contour = [ixp]
        prev_face = ixp.edge.r_face
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
                prev_face = first_ixp.edge.l_face
                ixp = next_ixp
                ix_points.remove(ixp)
                contour_is_open = True
                continue

            ### DEBUG
            # if ixp.edge not in this_edges_face.edges:
            #     print("type(ixp.edge): " + type(ixp.edge))
            #     print("type(face_edges): " + type(this_edges_face.edges[0]))
            #     raise ValueError("Edges aren't of same type")
            ### /DEBUG
            
            for cand_edge in this_edges_face.edges:
                if cand_edge is ixp.edge:
                    continue
                # if this candidate-edge crosses this intersection point's face,
                # it's x-point is the next point
                if (cand_edge, ixp.face) in self._saved_results:
                    next_ixp = self._saved_results[(cand_edge, ixp.face)]
                    if next_ixp is None:
                        continue
                    prev_face = this_edges_face
                    break
            ### DEBUG
            # if next_ixp is not None:
            #     print("Next ixp_found in this_edges_face.edges!")
            ### /DEBUG
                
            if next_ixp is None:
                # We didn't find it so the next xpoint must be on other face
                for cand_edge in ixp.face.edges:
                    if (cand_edge, this_edges_face) in self._saved_results:
                        next_ixp = self._saved_results[(cand_edge, this_edges_face)]
                        if next_ixp is None:
                            continue
                        prev_face = ixp.face
                        break
            ### DEBUG    
            # if next_ixp is not None:
            #     print("nextixp found in other face's edges!")
            ### /DEBUG

            if next_ixp is None:
                print("ix_points.len: %d" % len(ix_points))
                print("contour.len  : %d" % len(contour))
                raise ValueError ("couldn't find next intersection point")
            
            ixp = next_ixp
            contour.append(ixp)
            try:
                ix_points.remove(ixp)
            except ValueError:
                print("Couldn't remove ixp from ix_points!")
                print("len(ix_points): " + str(len(ix_points)))
                for an_ixp in ix_points:
                    print(str(an_ixp))
                if ixp is not None:
                    print("The point in question...")
                    print(str(ixp))
                

        return contour
        

    def _get_norm_squared(self, vector):
        return (vector[0]*vector[0] +
                vector[1]*vector[1] +
                vector[2]*vector[2])

    def _intersect_face_plane(self, face1, orientation, position):
        """ Compute intersection between a QEFace and an infinite plane
        Return a list of IntersectionPoints.
        """
        ix_points = []

        for edge in face1.edges:
            self._intersect_edge_plane(edge, orientation, position, ix_points)

        # if (len(ix_points) == 1 or
        #     len(ix_points) == 3):
        #     raise ValueError("Shouldn't happen")
        # else:
        #     print("normal result")
            
        return ix_points
    
    def _intersect_faces(self, face1, face2):
        """ compute intersection of two QEFace objects.
        Return a list of IntersectionPoints.
        """
        ix_points = []
        for edge in face1.edges:
            self._intersect_edge_face(edge, face2, ix_points)
        for edge in face2.edges:
            self._intersect_edge_face(edge, face1, ix_points)

        return ix_points

    def _intersect_edge_plane(self, edge, orientation, position, ix_points):
        """ Find the intersection between this edge and plane.
        Append the IntersectionPoint (if any) to ix_points.
        """
        if (edge, None) in self._saved_results:
            return self._saved_results[(edge, None)]

        if (edge.t_vert.pos[orientation] > position and
            edge.b_vert.pos[orientation] > position):
            point = None
        elif (edge.t_vert.pos[orientation] < position and
              edge.b_vert.pos[orientation] < position):
            point = None
        else:
            vec_t_vert = Vector((edge.t_vert.pos))
            vec_b_vert = Vector((edge.b_vert.pos))

            plane_co = Vector(([0,0,0]))
            plane_co[orientation] = position

            plane_norm = Vector(([0,0,0]))
            plane_norm[orientation] = 1.

            point = intersect_line_plane(vec_t_vert,
                                         vec_b_vert,
                                         plane_co,
                                         plane_norm,
                                         False) # only intersect segment

        if not point:
            ix_point = None
            # print("Not found!")
            # print("  t_vert: " + str(edge.t_vert.pos))
            # print("  b_vert: " + str(edge.b_vert.pos))
            # print("  pl_pos: " + str(position))
        else:
            # print("Found ixpoint! " + str(point))
            # print("  t_vert: " + str(vec_t_vert))
            # print("  b_vert: " + str(vec_b_vert))
            # print("  pl_pos: " + str(position))
            ix_point = IntersectionPoint(edge, None, point)
            ix_points.append(ix_point)
            
        self._saved_results[(edge, None)] = ix_point

        return ix_point
    
    def _intersect_edge_face(self, edge, face, ix_points):
        """ Compute intersection for one edge and one face.
        Returns None if no intersection occured, and a IntersectionPoint
        if one is found.
        """
        if (edge, face) in self._saved_results:
            return self._saved_results[(edge, face)]

        vec_t_vert = Vector((edge.t_vert.pos))
        vec_b_vert = Vector((edge.b_vert.pos))
        vec_dir = vec_t_vert - vec_b_vert
        
        point = intersect_ray_tri(Vector((face.verts[0].pos)),
                                  Vector((face.verts[1].pos)),
                                  Vector((face.verts[2].pos)),
                                  vec_dir,
                                  vec_b_vert,
                                  True) # restrict ix to tri face instead of plane
        # point = intersect_ray_tri(face.verts[0].get_blender_pos(),
        #                           face.verts[1].get_blender_pos(),
        #                           face.verts[2].get_blender_pos(),
        #                           edge.b_vert.get_blender_pos(),
        #                           dir_vector)

        if not point:
            ix_point = None
        elif (self._get_norm_squared(point - vec_b_vert) >
              self._get_norm_squared(vec_dir)):
            ix_point = None
        elif (point - vec_b_vert) * vec_dir < 0:
            ix_point = None
        else:
            # print ("Found ixpoint! " + str(point))
            ix_point = IntersectionPoint(edge, face, point)
            ix_points.append(ix_point)
            
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

    def __str__(self):
        ret = "Point info:\n"
        ret += "  point: (%1.5f, %1.5f, %1.5f)\n" % (self.point.x, self.point.y, self.point.z)
        ret += "  face: "
        if self.face is None:
            ret += " None\n"
        else:
            ret += str(self.face.verts) + "\n"
        ret += "  edge: (%d, %d)\n" % (self.edge.t_vert.index, self.edge.b_vert.index)
        return ret
