# -*- coding: utf-8 -*-
import pytest

from glassure.core.scattering_factors import *


@pytest.fixture
def form_factor_vitali():
    q = np.linspace(1, 12, 1000)
    form_factor_vitali = {
        'Si': 3.7464 * np.exp(-1.3104 * (q / 4 / np.pi) ** 2) + 1.4345 + 4.2959 * np.exp(
            -2.8652 * (q / 4 / np.pi) ** 2) + 3.5786 * np.exp(
            -36.3701 * (q / 4 / np.pi) ** 2) + .9544 * np.exp(
            -97.9643 * (q / 4 / np.pi) ** 2),
        'O': 1.3721 * np.exp(-.387 * (q / 4 / np.pi) ** 2) + .4348 + 2.0624 * np.exp(
            -5.5416 * (q / 4 / np.pi) ** 2) + 3.0566 * np.exp(
            -12.332 * (q / 4 / np.pi) ** 2) + 1.0743 * np.exp(
            -29.88 * (q / 4 / np.pi) ** 2),
        'Mg': 1.7214 * np.exp(-.5091 * (q / 4 / np.pi) ** 2) + .7801 + 6.1695 * np.exp(
            -3.4069 * (q / 4 / np.pi) ** 2) + 1.1777 * np.exp(
            -9.9868 * (q / 4 / np.pi) ** 2) + 2.1435 * np.exp(-80.4922 * (q / 4 / np.pi) ** 2),
        'Fe': 6.7127 * np.exp(-.3756 * (q / 4 / np.pi) ** 2) + 1.8157 + 12.076 * np.exp(
            -4.9535 * (q / 4 / np.pi) ** 2) + 3.2058 * np.exp(
            -16.7354 * (q / 4 / np.pi) ** 2) + 2.1868 * np.exp(
            -81.5166 * (q / 4 / np.pi) ** 2),
        'Ti': 6.6289 * np.exp(
            -0.6365 * (q / 4 / np.pi) ** 2) + 2.2032 + 9.9142 * np.exp(
            -8.2781 * (q / 4 / np.pi) ** 2) + 1.0215 * np.exp(
            -39.7076 * (q / 4 / np.pi) ** 2) + 2.2186 * np.exp(
            -100.4239 * (q / 4 / np.pi) ** 2)}
    return q, form_factor_vitali


def test_consistency_of_form_factor(form_factor_vitali):
    q, form_factor_vitali = form_factor_vitali
    # values from vitali's glass program
    form_factor_si = calculate_coherent_scattering_factor('Si', q)
    form_factor_O = calculate_coherent_scattering_factor('O', q)
    form_factor_Mg = calculate_coherent_scattering_factor('Mg', q)
    form_factor_Fe = calculate_coherent_scattering_factor('Fe', q)
    form_factor_Ti = calculate_coherent_scattering_factor('Ti', q)

    assert np.abs(np.sum(form_factor_si - form_factor_vitali['Si'])) < 1e-13
    assert np.abs(np.sum(form_factor_O - form_factor_vitali['O'])) < 1e-13
    assert np.abs(np.sum(form_factor_Mg - form_factor_vitali['Mg'])) < 1e-13
    assert np.abs(np.sum(form_factor_Fe - form_factor_vitali['Fe'])) < 1e-12
    assert np.abs(np.sum(form_factor_Ti - form_factor_vitali['Ti'])) < 1e-12


def test_consistency_of_incoherent_scattering(form_factor_vitali):
    q, form_factor_vitali = form_factor_vitali
    incoherent_vitali_si = (14 - (form_factor_vitali['Si'] ** 2) / 14) * (
            1 - .5254 * (np.exp(-1.1646 * (q / 4 / np.pi)) - np.exp(-14.3259 * (q / 4 / np.pi))))
    incoherent_vitali_o = (8 - (form_factor_vitali['O'] ** 2) / 8) * (
            1 - .3933 * (np.exp(-1.2843 * (q / 4 / np.pi)) - np.exp(-32.682 * (q / 4 / np.pi))))
    incoherent_vitali_mg = (12 - (form_factor_vitali['Mg'] ** 2) / 12) * (
            1 - 0.5189 * (np.exp(-1.2756 * (q / 4 / np.pi)) - np.exp(-15.3134 * (q / 4 / np.pi))))
    incoherent_vitali_fe = (26 - (form_factor_vitali['Fe'] ** 2) / 26) * (
            1 - 0.6414 * (np.exp(-0.9673 * (q / 4 / np.pi)) - np.exp(-10.4405 * (q / 4 / np.pi))))

    incoherent_si = calculate_incoherent_scattered_intensity('Si', q)
    incoherent_o = calculate_incoherent_scattered_intensity('O', q)
    incoherent_mg = calculate_incoherent_scattered_intensity('Mg', q)
    incoherent_fe = calculate_incoherent_scattered_intensity('Fe', q)

    assert np.abs(np.sum(incoherent_si - incoherent_vitali_si)) < 1e-12
    assert np.abs(np.sum(incoherent_o - incoherent_vitali_o)) < 1e-12
    assert np.abs(np.sum(incoherent_mg - incoherent_vitali_mg)) < 1e-12
    assert np.abs(np.sum(incoherent_fe - incoherent_vitali_fe)) < 1e-12


import matplotlib.pyplot as plt


def test_consistency_between_brown_and_hajdu_form_factors():
    hajdu_calculator = ScatteringFactorCalculatorHajdu()
    brown_calculator = ScatteringFactorCalculatorBrownHubbell()
    q = np.linspace(0, 10, 1000)
    for element in ['Si', 'O', 'Mg', 'Fe', 'Ti']:
        form_factor_hajdu = hajdu_calculator.get_coherent_scattering_factor(element, q)
        form_factor_brown = brown_calculator.get_coherent_scattering_factor(element, q)
        np.testing.assert_almost_equal(form_factor_hajdu, form_factor_brown, decimal=1)


def test_consistency_between_hubbell_and_hajdu_incoherent_intensity():
    hajdu_calculator = ScatteringFactorCalculatorHajdu()
    hubbell_calculator = ScatteringFactorCalculatorBrownHubbell()
    q = np.linspace(5, 20, 50)
    for element in ['Si', 'O', 'Mg', 'Fe', 'Ti']:
        incoherent_hajdu = hajdu_calculator.get_incoherent_intensity(element, q)
        incoherent_hubbell = hubbell_calculator.get_incoherent_intensity(element, q)

        # should be within 5 % of each other
        assert all(val > 0.95 for val in incoherent_hubbell / incoherent_hajdu)
        assert all(val < 1.05 for val in incoherent_hubbell / incoherent_hajdu)
