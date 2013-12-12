import sys
import copy

import bpy

from multiprocessing import Pool
from threading import Thread

from .quad_edge_mesh.quad_edge_mesh import QEMesh, QEVertex, QEFace, QEEdge

class BlenderQEMeshBuilder(object):
    """ Construct a BlenderQEMesh from a Blender Object.
    """
    @classmethod
    def construct_from_blender_object(cls, blender_object):
        """ Construct a BlenderQEMesh from a blender object
        """
        #if type(blender_object) is not bpy.blender.something

        # Call this twice
        blender_object.data.calc_tessface()
        blender_object.data.calc_tessface()
        bqem = BlenderQEMesh(blender_object)

        vidx_counter = 0
        for vert in blender_object.data.vertices:
            bqev = BlenderQEVertex(bqem, vidx_counter, vert.index)
            bqev.update_pos()
            bqem.add_vertex(bqev)
            vidx_counter = vidx_counter + 1

        # class variables for keeping current index number.
        # This really feels like a hack...
        cls.eidx_counter = 0
        cls.fidx_counter = 0

        # Tessfaces may be either tris or quads. We only want tris
        for face in blender_object.data.tessfaces:
            qef = cls._create_blender_triangle(bqem, [face.vertices[0],
                                                      face.vertices[1],
                                                      face.vertices[2]])
            bqem.add_face(qef)
            if len(face.vertices) > 3:
                qef = cls._create_blender_triangle(bqem, [face.vertices[0],
                                                          face.vertices[2],
                                                          face.vertices[3]])
                bqem.add_face(qef)

        return bqem

    @classmethod
    def _create_blender_triangle(cls, bqem, indices):
        qef = QEFace(bqem, cls.fidx_counter)
        cls.fidx_counter = cls.fidx_counter + 1

        nvs = len(indices)
        for ptidx in range(0, nvs):
            vidx = indices[ptidx]
            if ptidx+1 is nvs:
                vidx_1 = indices[0]
            else:
                vidx_1 = indices[ptidx+1]
            qef.verts.append(bqem.get_vertex(vidx))

            qee = bqem.get_edge_by_verts(vidx, vidx_1)
            if qee is None:
                qee = QEEdge(bqem, cls.eidx_counter)
                cls.eidx_counter = cls.eidx_counter + 1
                qee.b_vert = bqem.get_vertex(vidx)
                qee.t_vert = bqem.get_vertex(vidx_1)
                qee.l_face = qef
                try:
                    bqem.add_edge(qee)
                except ValueError:
                    print("vidx: %d, vidx_1: %d" % (vidx, vidx_1))
                    print("qee.b_vert: %d, qee.t_vert: %d" % (qee.b_vert.index, qee.t_vert.index))
                    raise ValueError("still nope")
            else:
                if qee.r_face is not None:
                    raise ValueError("This edge already has two faces.")
                qee.r_face = qef

            qef.edges.append(qee)

        for face_eidx in range(0, len(qef.edges)):
            # Update the rest of the edges internal pointers 
            qee = qef.edges[face_eidx]

            if qee.r_face is None:
                if face_eidx+1 is len(qef.edges):
                    qee.tl_edge = qef.edges[0]
                    qee.bl_edge = qef.edges[0]
                else:
                    qee.tl_edge = qef.edges[face_eidx+1]
                    qee.bl_edge = qef.edges[face_eidx+1]
            else:
                # else this is the right face
                if face_eidx+1 is len(qef.edges):
                    qee.br_edge  = qef.edges[0]
                else:
                    qee.br_edge  = qef.edges[face_eidx+1]
                if face_eidx == 0:
                    qee.tr_edge = qef.edges[-1]
                else:
                    qee.tr_edge = qef.edges[face_eidx-1]
                    
        if len(qef.edges) is not len(qef.verts):
            raise ValueError("This seems strange...")

        return qef

def update_one_vertex_no_matrix(vert):
    vert.update_pos_no_matrix()

def update_vertex_list_no_matrix(verts, blobj):
    for vert in verts:
        vert.update_pos_no_matrix_blobj(blobj)

class BlenderQEMesh(QEMesh):
    """ A QEMesh that also stores some Blender specific info.
    """
    def __init__(self, blender_object):
        super(BlenderQEMesh, self).__init__()
        self.blender_name = blender_object.name
        self.is_rigid = True

    def get_blender_object(self):
        return bpy.data.objects[self.blender_name]

    def get_matrix_world(self):
        return self.get_blender_object().matrix_world

    def is_updated(self):
        return self.get_blender_object().is_updated

    def update_vertex_positions(self):
        self.blobj = self.get_blender_object().data.vertices
        if self.is_rigid:
            for vert in self._vertices:
                vert.update_pos()
        else:
            for vert in self._vertices:
                vert.update_pos_no_matrix()

    def update_vertex_positions_mt(self):
        num_procs = 16
        pool = Pool(processes = num_procs)
        self.blobj = self.get_blender_object().data.vertices
        
        pool.imap(update_one_vertex_no_matrix, self._vertices, len(self._vertices)//8)
        pool.close()
        pool.join()

    def update_vertex_positions_mt2(self):
        num_procs = 8
        threads = []
        num_verts = len(self._vertices)
        slice_size = num_verts//num_procs
        blobj = self.get_blender_object()
        
        for i in range(num_procs):
            if (i+1) == num_procs:
                threads.append(Thread(target=update_vertex_list_no_matrix,
                                      args=(self._vertices[i*slice_size:], blobj.data.vertices)))
            else:
                threads.append(Thread(target=update_vertex_list_no_matrix,
                                  args=(self._vertices[i*slice_size:(i+1)*slice_size],blobj.data.vertices)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()
                                  

class BlenderQEVertex(QEVertex):
    """ A QEVertex that links to Blender vertices.
    """
    def __init__(self, parent_mesh, index, blender_vert_index):
        super(BlenderQEVertex, self).__init__(parent_mesh, index)
        self.blender_vindex = blender_vert_index
        self.blender_pos = None
        self.is_updated = True
        self.EPSILON = 1e-8

    def get_pos(self):
        bl_pos = self.mesh.get_blender_object().data.vertices[self.blender_vindex]
        
        bl_world_pos = self.mesh.get_matrix_world() * bl_pos.co

        return bl_world_pos
        

    def update_pos_no_matrix(self):
        #bl_pos = self.mesh.get_blender_object().data.vertices[self.blender_vindex]
        bl_pos = self.mesh.blobj[self.blender_vindex]

        if (abs(self.pos[0] - bl_pos.co[0]) < self.EPSILON and
            abs(self.pos[1] - bl_pos.co[1]) < self.EPSILON and
            abs(self.pos[2] - bl_pos.co[2]) < self.EPSILON):
            self.is_updated = False
        else:
            self.is_updated = True
        #self.is_updated = True
        self.pos[0] = bl_pos.co[0]
        self.pos[1] = bl_pos.co[1]
        self.pos[2] = bl_pos.co[2]
        
    def update_pos_no_matrix_blobj(self, blobj):
        bl_pos = blobj[self.blender_vindex]

        if (abs(self.pos[0] - bl_pos.co[0]) < self.EPSILON and
            abs(self.pos[1] - bl_pos.co[1]) < self.EPSILON and
            abs(self.pos[2] - bl_pos.co[2]) < self.EPSILON):
            self.is_updated = False
        else:
            self.is_updated = True
        #self.is_updated = True
        self.pos[0] = bl_pos.co[0]
        self.pos[1] = bl_pos.co[1]
        self.pos[2] = bl_pos.co[2]
        
        
    def update_pos(self):
        """ Update the position of this Blender vertex.
        Does not check if mesh has been updated. Will multiply by matrix_world.
        """
        bl_pos = self.mesh.get_blender_object().data.vertices[self.blender_vindex]

        self.is_updated = True

        bl_world_pos = self.mesh.get_matrix_world() * bl_pos.co
        self.pos[0] = bl_world_pos[0]
        self.pos[1] = bl_world_pos[1]
        self.pos[2] = bl_world_pos[2]
        
        # print(self.mesh.blender_name + " pos: " + str(self.pos))

    
