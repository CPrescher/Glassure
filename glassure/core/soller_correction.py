# -*- coding: utf-8 -*-

import numpy as np


class SollerCorrection(object):
    def __init__(self, two_theta, max_thickness, inner_radius=62, outer_radius=210,
                 inner_width=0.05, outer_width=0.2, inner_length=8, outer_length=6):
        """
        This class handles the calculation of the intensity correction when using soller slits. Upon initialization it
        creates a lookup table for the dispersion angles for each two theta angle and thickness of the sample.

        Corrections are then calculated

        :param two_theta: angles for which the correction needs to be done (in Degree)
        :param max_thickness: maximum sample thickness for which the lookup table (in mm)
        :param inner_radius: radius where the inner slits start (in mm)
        :param outer_radius: radius where the outer slits start (in mm)
        :param inner_width: width of the inner slits (in mm)
        :param outer_width: width of the outer slits (in mm)
        :param inner_length: length of the slit blades (in mm)
        :param outer_length: length of the slit blades (in mm)
        """

        self._two_theta = two_theta / 180. * np.pi
        self._max_thickness = max_thickness
        self._inner_radius = inner_radius
        self._outer_radius = outer_radius
        self._inner_width = inner_width
        self._outer_width = outer_width
        self._inner_length = inner_length
        self._outer_length = outer_length

        self.dispersion_angle_map = self.calculate_dispersion_angle_map()

    def calculate_dispersion_angle_map(self):
        """
        Creates a lookup table of dispersion angles for each two theta value and distance from the center of the
        soller slit rotation center
        :return: a map of the dispersion anges, out.X = two theta array, out.Y = distance array, out.data = dispersion
        angle
        """
        p_x = np.arange(-self._max_thickness * 0.5, self._max_thickness * 0.5, 0.001)
        p_y = np.zeros(p_x.shape)
        p = np.array([p_x, p_y])
        phi_array = []
        for two_theta_value in self._two_theta:
            # calculate fix points for the ther outer parts of the slits
            q1_1, q1_2 = calculate_rectangular_side_points(self._inner_radius + self._inner_length,
                                                           two_theta_value, self._inner_width)

            q2_1, q2_2 = calculate_rectangular_side_points(self._outer_radius + self._outer_length,
                                                           two_theta_value, self._outer_width)

            # calculate fix points for the inner parts of the slits
            s1_1, s1_2 = calculate_rectangular_side_points(self._inner_radius, two_theta_value, self._inner_width)

            # calculate the angles to the outer points of the slits
            phi1 = calculate_angles(q1_1, q1_2, p)
            phi2 = calculate_angles(q2_1, q2_2, p)
            phi3 = calculate_angles(q2_1, q1_2, p)
            phi4 = calculate_angles(q1_1, q2_2, p)

            # take the smallest angle for each point
            phi = np.where(phi1 < phi2, phi1, phi2)
            phi = np.where(phi3 < phi, phi3, phi)
            phi = np.where(phi4 < phi, phi4, phi)

            # getting geometry
            intercept_s1_2_q1_1 = calculate_x_axis_intercept(s1_2, q1_1)
            intercept_s1_2_q2_1 = calculate_x_axis_intercept(s1_2, q2_1)
            intercept_q1_2_q2_2 = calculate_x_axis_intercept(q1_2, q2_2)

            intercept_s1_1_q2_2 = calculate_x_axis_intercept(s1_1, q2_2)
            intercept_q1_1_q2_1 = calculate_x_axis_intercept(q1_1, q2_1)

            pos_cutoff = 0 if intercept_q1_2_q2_2 < 0 else intercept_q1_2_q2_2
            neg_cutoff = 0 if intercept_q1_1_q2_1 > 0 else intercept_q1_1_q2_1

            #####################
            # correcting for positive side:

            intermediate_region_ind = np.logical_and(p_x > pos_cutoff, p_x < intercept_s1_2_q1_1)
            points_in_intermediate_region = p[:, intermediate_region_ind]

            if np.sum(intermediate_region_ind):
                phi1 = calculate_angles(s1_2, q2_1, points_in_intermediate_region)
                phi2 = calculate_angles(q2_2, q2_1, points_in_intermediate_region)
                phi[intermediate_region_ind] = np.where(phi1 < phi2, phi1, phi2)

            # cut the angle
            phi[p[0] > intercept_s1_2_q1_1] = 0
            phi[p[0] > intercept_s1_2_q2_1] = 0

            ########################
            # correcting for negative side:

            intermediate_region_ind = np.logical_and(p_x < neg_cutoff, p_x > intercept_s1_1_q2_2)
            points_in_intermediate_region = p[:, intermediate_region_ind]

            if np.sum(intermediate_region_ind):
                phi1 = calculate_angles(s1_1, q2_2, points_in_intermediate_region)
                phi2 = calculate_angles(q2_1, q2_2, points_in_intermediate_region)
                phi[intermediate_region_ind] = np.where(phi1 < phi2, phi1, phi2)

            intercept_s1_1_q2_2 = calculate_x_axis_intercept(s1_1, q2_2)
            phi[p[0] < intercept_s1_1_q2_2] = 0

            phi_array.append(phi)

        # create the real grid
        two_theta_array_deg = self._two_theta / np.pi * 180
        X, Y = np.meshgrid(two_theta_array_deg, p[0])
        phi_array = np.array(phi_array).transpose()

        return Map(X, Y, phi_array)

    def transfer_function_from_region(self, d1, d2):
        """
        Calculates the transfer function for a sample region within d1 and d2
        :param d1: lower bound of the sample region
        :param d2: upper bound of the sample region
        :return: transfer function with same dimensions as two_theta
        """
        distance = self.dispersion_angle_map.Y[:, 0]
        region_ind = np.logical_and(distance > d1, distance < d2)
        transfer_function = 1. / np.sum(self.dispersion_angle_map.data[region_ind, :], 0)
        transfer_function = transfer_function / np.min(transfer_function)
        return transfer_function

    def transfer_function_sample(self, sample_thickness, shift=0):
        """
        Calculates the transfer function for a specific sample thickness, assuming the sample is centered, to the
        rotation center of the soller slit
        :param sample_thickness: sample thickness in mm
        :param shift: shift of the sample relative to rotation center of the soller slit in beam direction (x)
        :return: transfer function with same dimensions as two_theta
        """
        return self.transfer_function_from_region(-sample_thickness * 0.5 + shift,
                                                  +sample_thickness * 0.5 + shift)

    def transfer_function_dac(self, sample_thickness, initial_thickness):
        """
        Calculates two transfer function specific to diamond anvil cell (DAC) correction. It calculates the transfer
        function for the sample and also for the Compton scattering of diamonds which came into the diffraction volume
        due to the compression.
        :param sample_thickness: current sample thickness in mm
        :param initial_thickness: initial sample chamber thickness when background was measured, in mm
        :return: tuple of (sample transfer function, diamond transfer function), both with same dimensions as two_theta
        """
        sample_transfer_function = self.transfer_function_sample(sample_thickness)
        d1 = sample_thickness * 0.5
        d2 = initial_thickness * 0.5
        diamond_transfer_function = self.transfer_function_from_region(d1, d2)
        diamond_transfer_function += self.transfer_function_from_region(-d2, -d1)
        diamond_transfer_function /= 2
        return sample_transfer_function, diamond_transfer_function
    
class SollerCorrectionGui(SollerCorrection):
    def __init__(self,  q, wavelength, max_thickness, inner_radius=62, outer_radius=210,
                 inner_width=0.05, outer_width=0.2, inner_length=8, outer_length=6):

        two_theta = np.arcsin(q * wavelength / (4 * np.pi)) * 360 / np.pi
        super(SollerCorrectionGui, self).__init__(two_theta, max_thickness, inner_radius, outer_radius,
                 inner_width, outer_width, inner_length, outer_length)
        self.wavelength = wavelength
        self.q = q


# Utility functions and classes
class Map(object):
    def __init__(self, X, Y, data):
        self.X = X
        self.Y = Y
        self.data = data


def vector_length(vec):
    return np.sqrt(np.sum(vec ** 2))


def calculate_angles(point1, point2, p):
    """
    calculates the angle between vectors going from the two points (point1, point2) to a central point p using
    the dot product.
    """
    return np.arccos(((point1[0] - p[0]) * (point2[0] - p[0]) + (point1[1] - p[1]) * (point2[1] - p[1])) /
                     (np.sqrt((point1[0] - p[0]) ** 2 + (point1[1] - p[1]) ** 2) * np.sqrt(
                         (point2[0] - p[0]) ** 2 + (point2[1] - p[1]) ** 2)))


def calculate_x_axis_intercept(p1, p2):
    """
    obtains the x-axis intercept of a line defined by two points.
    """
    m = (p2[1] - p1[1]) / (p2[0] - p1[0])
    c = p2[1] - p2[0] * m
    return -c / m


def calculate_y_axis_intercept(p1, p2):
    """
    obtains the y-axis intercept of a line defined by two points.
    """
    m = (p2[1] - p1[1]) / (p2[0] - p1[0])
    return m * (-p2[0]) + p2[1]


def calculate_rectangular_side_points(radius, angle, width):
    """
    calculates the points which are rectangularly width/2 away at a certain angle, radius combination
    :return: 2 points with (x, y) coordinates
    """
    p1 = np.array([radius * np.cos(angle) - 0.5 * width * np.sin(angle),
                   radius * np.sin(angle) + 0.5 * width * np.cos(angle)])

    p2 = np.array([radius * np.cos(angle) + 0.5 * width * np.sin(angle),
                   radius * np.sin(angle) - 0.5 * width * np.cos(angle)])

    return p1, p2
