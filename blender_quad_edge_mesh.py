import copy

import bpy

import quad_edge_mesh

class BlenderQEMeshBuilder(object):
    """ Construct a BlenderQEMesh from a Blender Object.
    """
    @classmethod
    def construct_from_blender_object(cls, blender_object):
        """ Construct a BlenderQEMesh from a blender object
        """
        #if type(blender_object) is not bpy.blender.something

        blender_object.calc_tessface()
        bqem = BlenderQEMesh(blender_object)

        vidx_counter = 0
        for vert in blender_object.vertices:
            bqev = BlenderQEVertex(bqem, vidx_counter, vert.index)
            bqev.update_pos() 
            vidx_counter = vidx_counter + 1


        eidx_counter = 0
        fidx_counter = 0
        
        for face in blender_object.tessfaces:
            indices = copy.deepcopy(face.vertices)
            qef = quad_edge_mesh.QEFace(bqem, fidx_counter)
            fidx_counter = fidx_counter + 1
            
            nvs = len(indices)
            for ptidx in range(0, nvs):
                vidx = indices[ptidx]-1
                if ptidx+1 is nvs:
                    vidx_1 = indices[0]-1
                else:
                    vidx_1 = indices[ptidx+1]-1
                qef.verts.append(vidx)

                qee = bqem.get_edge_by_verts(vidx, vidx_1)
                if qee is None:
                    qee = quad_edge_mesh.QEEdge(bqem, eidx_counter)
                    eidx_counter = eidx_counter + 1
                    qee.b_vert = vidx
                    qee.t_vert = vidx_1
                    qee.l_face = qef
                    bqem.add_edge(qee)
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
                raise ValueError("Uh oh")
            bqem.add_face(qef)

        return bqem

class BlenderQEMesh(quad_edge_mesh.QEMesh):
    """ A QEMesh that also stores some Blender specific info.
    """
    def __init__(self, blender_object):
        super(BlenderQEMesh, self).__init__()
        self.blender_name = blender_object.name

    def get_blender_object(self):
        return bpy.data.objects[self.blender_name]

    def get_matrix_world(self):
        return self.get_blender_object().matrix_world

    def is_updated(self):
        return self.get_blender_object().is_updated

    def update_vertex_positions(self):
        if self.is_updated():
            for vert in super.vertices:
                vert.update_pos()
        

class BlenderQEVertex(quad_edge_mesh.QEVertex):
    """ A QEVertex that links to Blender vertices.
    """
    def __init__(self, parent_mesh, index, blender_vert_index):
        super(BlenderQEVertex, self).__init__(parent_mesh, index)
        self.blender_vindex = blender_vert_index

    def update_pos(self):
        """ Update the position of this Blender vertex.
        Does not check if mesh has been updated. Will multiply by matrix_world.
        """
        bl_pos = self.mesh.get_blender_object().data.vertices[self.blender_vindex]
        bl_world_pos = self.mesh.get_matrix_world() * bl_pos
        self.pos[0] = bl_world_pos[0]
        self.pos[1] = bl_world_pos[1]
        self.pos[2] = bl_world_pos[2]
        
    
