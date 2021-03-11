# -*- coding: utf-8 -*- 
# @Time : 2020/9/10 16:37 
# @Author : CaiXin
# @File : PointCloudMapping.py
import random
import numpy as np
import open3d as o3d

from utils.UtilsMisc import getGraphNodePose


def random_sampling(orig_points, num_points):
    if orig_points.shape[0] > num_points:
        points_down_idx = random.sample(range(orig_points.shape[0]), num_points)
        down_points = orig_points[points_down_idx, :]
        return down_points
    else:
        return orig_points


def showPointcloudFromFile(filename=None):
    if filename is None:
        print("No file input...")
    else:
        pointcloud = o3d.io.read_point_cloud(filename)
        o3d.visualization.draw_geometries([pointcloud], window_name='Map_' + filename)


class MappingManager:
    def __init__(self):
        # internal vars
        self.global_ptcloud = None # numpy type
        self.curr_local_ptcloud = None
        self.ptcloud_list = []
        self.curr_se3 = np.identity(4)

        self.pointcloud = o3d.geometry.PointCloud()# open3d type
        # visualizaton
        self.viz=None


    def updateMap(self, down_points=100):
        # 将点云坐标转化为齐次坐标（x,y,z）->(x,y,z,1)
        self.curr_local_ptcloud = random_sampling(self.curr_local_ptcloud, down_points)
        tail = np.zeros((self.curr_local_ptcloud.shape[0], 1))
        tail.fill(1)
        self.curr_local_ptcloud = np.concatenate([self.curr_local_ptcloud, tail], axis=1)
        self.ptcloud_list.append(self.curr_local_ptcloud)
        sub_ptcloud_map = self.curr_se3 @ (self.curr_local_ptcloud.T)

        # concatenate the latest local pointcloud into global pointcloud
        if (self.global_ptcloud is None):
            self.global_ptcloud = sub_ptcloud_map.T[:, :3]
        else:
            self.global_ptcloud = np.concatenate([self.global_ptcloud, sub_ptcloud_map.T[:, :3]])
        # updata open3d_pointscloud
        self.pointcloud.points=o3d.utility.Vector3dVector(self.global_ptcloud)

    def optimizeGlobalMap(self, graph_optimized, curr_node_idx=None):
        global_ptcloud = None
        se3 = np.identity(4)
        for i in range(curr_node_idx):
            pose_trans, pose_rot = getGraphNodePose(graph_optimized, i)
            se3[:3, :3] = pose_rot
            se3[:3, 3] = pose_trans
            sub_ptcloud_map = se3 @ (self.ptcloud_list[i].T)
            if (global_ptcloud is None):
                global_ptcloud = sub_ptcloud_map.T[:, :3]
            else:
                global_ptcloud = np.concatenate([global_ptcloud, sub_ptcloud_map.T[:, :3]])

        self.global_ptcloud = global_ptcloud
        self.pointcloud.points=o3d.utility.Vector3dVector(self.global_ptcloud)
        # correct current pose
        pose_trans, pose_rot = getGraphNodePose(graph_optimized, curr_node_idx)
        self.curr_se3[:3, :3] = pose_rot
        self.curr_se3[:3, 3] = pose_trans

    def vizMapWithOpen3D(self):
        if self.viz==None:
            self.viz = o3d.visualization.Visualizer()
            self.viz.create_window()
            # self.viz.get_render_option().point_size = 2.0
            # self.viz.get_render_option().point_color_option = o3d.visualization.PointColorOption.XCoordinate
            self.viz.add_geometry(self.pointcloud)
            # self.viz.add_geometry(o3d.geometry.TriangleMesh.create_coordinate_frame(size=400, origin=[0., 0., 0.]))
        if self.global_ptcloud is not None:
            self.pointcloud.points = o3d.utility.Vector3dVector(self.global_ptcloud)
            self.viz.update_geometry()
            self.viz.poll_events()
            self.viz.update_renderer()

    def saveMap2File(self, filename=None):
        if self.global_ptcloud is not None:
            o3d.io.write_point_cloud(filename, self.pointcloud)


