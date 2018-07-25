## example usage
# ---------------
# import POTreeReader
# from shapely.geometry import Polygon
# folder = '/home/bramalingam/src/PotreeConverter_oxfordni/build/potree_converted_locb_test/data/r/'
# potree = PoTree(folder)
# bounding_box = Polygon([(725, 574) , (778, 574), (778, 520), (725, 520)]) 
# points = potree.get_points(bounding_box)
# print(points)

import glob, os
import csv
import numpy as np
import matplotlib.pyplot as plt
from laspy.file import File
from shapely.geometry import Polygon
from descartes.patch import PolygonPatch
import struct

# calculates bounding box (shapely polygon) for the octree node
def get_bounding_box(inFile):
    header = inFile.header
    header_min = header.min
    header_max = header.max
    x_min = header_min[0]
    y_min = header_min[1]
    z_min = header_min[2]
    x_max = header_max[0]
    y_max = header_max[1]
    z_max = header_max[2]
    bounding_box = Polygon([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)])
    return bounding_box

class PoTree:
    # initializes the PoTree class and reads the PoTree las files from every node,
    # computes the bounding boxes for every node from the las headers for the node
    def __init__(self, foldername):

        file_names = sorted(glob.glob(foldername + '*.las'))
        point_counter = 0
        nodes_bounding_box = {}
        for file in file_names:
            inFile = File(file, mode='r')
            point_counter = point_counter + inFile.get_header().get_count()
            nodes_bounding_box[file] = get_bounding_box(inFile)

        self.num_points = point_counter 
        self.nodes_bounding_box = nodes_bounding_box

    # returns a dictionary of points at multiple resolutions
    def get_points(self, bounding_box):

        points = {}
        for filename in self.nodes_bounding_box.keys():

            if self.nodes_bounding_box[filename].intersects(bounding_box):
                # read las file from the node
                inFile = File(filename, mode='r')
                # read the extra bytes from the object (if present)
                # this is where all the extra attributes part of the locb point schema live
                extra_attributes = inFile.extra_bytes

                # 2 attributes added as extra bytes to the LAS schema:
                # first two bytes: channelIndex, second two bytes: frameIndex
                attributes = np.empty([extra_attributes.size, 2], dtype=int)
                for point_index, point_attribute in enumerate(extra_attributes):
                    attributes[point_index] = struct.unpack("=HH", extra_attributes[point_index])
                
                channel_index = attributes[:, 0]  # no offset or scaling added to this attribute
                frame_index = attributes[:, 1] # no offset or scaling added to this attribute

                # resolution level estimation from the filename
                # reference for documentation : 
                # data and index files section of https://github.com/potree/potree/blob/develop/docs/potree-file-format.md
                level = len(filename.rsplit('/', 1)[-1])
                coords = np.vstack((inFile.x, inFile.y, inFile.z, channel_index, frame_index, inFile.intensity)).transpose()

                # append points for a certain resolution from the octree to the dictionary
                if level not in points:
                    points[level] = coords
                else:
                    points[level] = np.vstack((points[level], coords))

        return points

    # plot the bounding boxes of the multiple resolutions
    def plot_resolution_levels(self, bounding_box):

        fig, ax = plt.subplots(1,1)
        for filename in self.nodes_bounding_box.keys():

            if self.nodes_bounding_box[filename].intersects(bounding_box):
                inFile = File(filename, mode='r')
                bounding_box1 = get_bounding_box(inFile)
                ax.add_patch(PolygonPatch(bounding_box1, alpha=0.3))

        ax.set_xlim([0, 1000])
        ax.set_ylim([0, 1000])
        plt.show()
