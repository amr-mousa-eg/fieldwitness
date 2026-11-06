"""Daily FAO Penman-Monteith grass reference evapotranspiration (T3.1).

Source: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration.
FAO Irrigation and Drainage Paper 56, HTML edition (1998), read on 2026-11-04 from the equation
images and text of the chapter pages (local copies in the gitignored `docs/refs/fao56_eq/`):
  Ch. 3  https://www.fao.org/4/x0490e/x0490e07.htm  (Eq. 7, 8, 11-13, 17, 19, 21, 23-25, 34, 35,
                                                      37-40, 42 and the constants used here)
  Ch. 4  https://www.fao.org/4/x0490e/x0490e08.htm  (Eq. 6; Example 18, the check in
                                                      tests/test_eto.py)
The 2nd edition (2025) exists but is not used, for consistency with config/crops.yaml.

Units: temperature °C, pressure kPa, radiation MJ m-2 day-1, wind m/s at 2 m, ETo mm/day.
All functions take scalars or numpy arrays.
"""

import numpy as np

G_SC = 0.0820  # solar constant, MJ m-2 min-1 (Ch. 3, Eq. 21 symbol list)
SIGMA = 4.903e-9  # Stefan-Boltzmann constant, MJ K-4 m-2 day-1 (Ch. 3, Eq. 39 symbol list)
ALBEDO_GRASS = 0.23  # albedo of the hypothetical grass reference (Ch. 3, Eq. 38 symbol list)
KELVIN = 273.16  # "adding 273.16 to the temperature expressed in °C" (Ch. 3, Eq. 39 text)
AS_DEFAULT, BS_DEFAULT = 0.25, 0.50  # Angstrom values recommended without calibration (Ch. 3)


def pressure(z_m):
    """Atmospheric pressure, kPa, from elevation z (m). FAO-56 Eq. 7."""
    return 101.3 * ((293.0 - 0.0065 * z_m) / 293.0) ** 5.26


def psychrometric_constant(p_kpa):
    """Psychrometric constant gamma, kPa/°C. FAO-56 Eq. 8 (0.665e-3 P)."""
    return 0.665e-3 * p_kpa


def sat_vp(t_c):
    """Saturation vapour pressure e°(T), kPa. FAO-56 Eq. 11."""
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


def mean_sat_vp(tmax, tmin):
    """Mean saturation vapour pressure es, kPa. FAO-56 Eq. 12."""
    return (sat_vp(tmax) + sat_vp(tmin)) / 2.0


def slope_vp(t_c):
    """Slope of the saturation vapour pressure curve, kPa/°C. FAO-56 Eq. 13."""
    return 4098.0 * sat_vp(t_c) / (t_c + 237.3) ** 2


def actual_vp_rh_minmax(tmax, tmin, rhmax, rhmin):
    """Actual vapour pressure ea, kPa, from RHmax and RHmin (%). FAO-56 Eq. 17."""
    return (sat_vp(tmin) * rhmax / 100.0 + sat_vp(tmax) * rhmin / 100.0) / 2.0


def actual_vp_rh_mean(tmax, tmin, rhmean):
    """Actual vapour pressure ea, kPa, from mean RH (%), e.g. POWER RH2M. FAO-56 Eq. 19."""
    return rhmean / 100.0 * mean_sat_vp(tmax, tmin)


def _dr_delta_ws(lat_deg, doy):
    phi = np.pi / 180.0 * lat_deg  # Eq. 22
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi / 365.0 * doy)  # Eq. 23
    delta = 0.409 * np.sin(2.0 * np.pi / 365.0 * doy - 1.39)  # Eq. 24
    ws = np.arccos(-np.tan(phi) * np.tan(delta))  # Eq. 25
    return phi, dr, delta, ws


def extraterrestrial_radiation(lat_deg, doy):
    """Ra, MJ m-2 day-1, from latitude (decimal degrees, south negative) and day of year J.
    FAO-56 Eq. 21 with Eq. 22-25."""
    phi, dr, delta, ws = _dr_delta_ws(lat_deg, doy)
    return (
        24.0
        * 60.0
        / np.pi
        * G_SC
        * dr
        * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    )


def daylight_hours(lat_deg, doy):
    """Maximum possible sunshine duration N, hours. FAO-56 Eq. 34."""
    return 24.0 / np.pi * _dr_delta_ws(lat_deg, doy)[3]


def solar_radiation_angstrom(n_hours, lat_deg, doy, a_s=AS_DEFAULT, b_s=BS_DEFAULT):
    """Rs, MJ m-2 day-1, from sunshine hours n. FAO-56 Eq. 35 (not needed with POWER Rs)."""
    return (a_s + b_s * n_hours / daylight_hours(lat_deg, doy)) * extraterrestrial_radiation(
        lat_deg, doy
    )


def clear_sky_radiation(ra, z_m):
    """Rso, MJ m-2 day-1, without calibrated a_s, b_s. FAO-56 Eq. 37."""
    return (0.75 + 2e-5 * z_m) * ra


def net_shortwave(rs, albedo=ALBEDO_GRASS):
    """Rns, MJ m-2 day-1. FAO-56 Eq. 38."""
    return (1.0 - albedo) * rs


def net_longwave(tmax, tmin, ea, rs, rso):
    """Rnl, MJ m-2 day-1. FAO-56 Eq. 39 (temperatures converted with +273.16 K)."""
    tk4 = ((tmax + KELVIN) ** 4 + (tmin + KELVIN) ** 4) / 2.0
    return SIGMA * tk4 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rs / rso - 0.35)


def eto_daily(tmax, tmin, rs, u2, ea, z_m, lat_deg, doy, g=0.0):
    """Daily grass reference ETo, mm/day. FAO-56 Eq. 6, with Rn = Rns - Rnl (Eq. 38-40) and
    soil heat flux G = 0 for day periods (Eq. 42). Delta at Tmean (Eq. 13), gamma from P (Eq. 7-8),
    es from Eq. 12, Ra from Eq. 21 and Rso from Eq. 37, as in Example 18 (Ch. 4)."""
    tmean = (tmax + tmin) / 2.0
    delta = slope_vp(tmean)
    gamma = psychrometric_constant(pressure(z_m))
    es = mean_sat_vp(tmax, tmin)
    rso = clear_sky_radiation(extraterrestrial_radiation(lat_deg, doy), z_m)
    rn = net_shortwave(rs) - net_longwave(tmax, tmin, ea, rs, rso)  # Eq. 40
    num = 0.408 * delta * (rn - g) + gamma * 900.0 / (tmean + 273.0) * u2 * (es - ea)
    return num / (delta + gamma * (1.0 + 0.34 * u2))
