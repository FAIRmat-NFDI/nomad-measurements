import numpy as np
import plotly.express as px
from scipy.interpolate import griddata

def plot_1d(x, y):
    '''
    Plot the 1D diffractogram.

    Args:
        x (np.ndarray): array of x values
        y (np.ndarray): array of y values

    Returns:
        (dict, dict): line_linear, line_log
    '''
    fig_line_linear = px.line(
        x = x,
        y = y,
        labels = {
            'x': '2θ (°)',
            'y': 'Intensity',
        },
        title = 'Intensity (linear scale)',
    )
    json_line_linear = fig_line_linear.to_plotly_json()

    fig_line_log = px.line(
        x = x,
        y = y,
        log_y = True,
        labels = {
            'x': '2θ (°)',
            'y': 'Intensity',
        },
        title = 'Intensity (log scale)',
    )
    json_line_log = fig_line_log.to_plotly_json()

    return json_line_linear, json_line_log

def plot_2d_range(ax1, ax2):
    '''
    Calculate the range of the 2D plot for generation of regular grid.
    Finds the smallest box that can contain the data.

    Args:
        ax1 (np.ndarray): array of first axis values
        ax2 (np.ndarray): array of second axis values

    Returns:
        (list, list): ax1_range, ax2_range
    '''
    ax1_range_length = np.max(ax1) - np.min(ax1)
    ax2_range_length = np.max(ax2) - np.min(ax2)

    if ax1_range_length > ax2_range_length:
        ax1_range = [np.min(ax1),np.max(ax1)]
        ax2_mid = np.min(ax2) + ax2_range_length/2
        ax2_range = [
            ax2_mid-ax1_range_length/2,
            ax2_mid+ax1_range_length/2,
        ]
    else:
        ax2_range = [np.min(ax2),np.max(ax2)]
        ax1_mid = np.min(ax1) + ax1_range_length/2
        ax1_range = [
            ax1_mid-ax2_range_length/2,
            ax1_mid+ax2_range_length/2,
        ]

    return ax1_range, ax2_range

def plot_2d_rsm(two_theta, omega, q_parallel, q_perpendicular, intensity):
    '''
    Plot the 2D RSM diffractogram.

    Args:
        two_theta (pint.Quantity): array of 2θ values
        omega (pint.Quantity): array of ω values
        q_parallel (pint.Quantity): array of Q_parallel values
        q_perpendicular (pint.Quantity): array of Q_perpendicular values
        intensity (pint.Quantity): array of intensity values

    Returns:
        (dict, dict): json_2theta_omega, json_q_vector
    '''
    # Plot for 2theta-omega RSM
    x = omega.magnitude
    y = two_theta.magnitude
    log_z = np.log10(intensity)
    x_range, y_range = plot_2d_range(x, y)

    fig_2theta_omega = px.imshow(
        img = np.around(log_z,3).T,
        x = np.around(x,3),
        y = np.around(y,3),
        color_continuous_scale = 'inferno',
    )
    fig_2theta_omega.update_layout(
        title = 'RSM plot: Intensity (log-scale) vs Axis position',
        xaxis_title = 'ω (°)',
        yaxis_title = '2θ (°)',
        xaxis = dict(
            autorange = False,
            fixedrange = False,
            range = x_range,
        ),
        yaxis = dict(
            autorange = False,
            fixedrange = False,
            range = y_range,
        ),
        width = 600,
        height = 600,
    )
    json_2theta_omega = fig_2theta_omega.to_plotly_json()

    # Plot for RSM in Q-vectors
    if q_parallel is not None and q_perpendicular is not None:
        x = q_parallel.to('1/angstrom').magnitude.flatten()
        y = q_perpendicular.to('1/angstrom').magnitude.flatten()
        # q_vectors lead to irregular grid
        # generate a regular grid using interpolation
        x_regular = np.linspace(x.min(),x.max(),intensity.shape[0])
        y_regular = np.linspace(y.min(),y.max(),intensity.shape[1])
        x_grid, y_grid = np.meshgrid(x_regular,y_regular)
        z_interpolated = griddata(
            points = (x,y),
            values = intensity.flatten(),
            xi = (x_grid,y_grid),
            method = 'linear',
            fill_value = intensity.min(),
        )
        log_z_interpolated = np.log10(z_interpolated)
        x_range, y_range = plot_2d_range(x_regular,y_regular)

        fig_q_vector = px.imshow(
            img = np.around(log_z_interpolated,3),
            x = np.around(x_regular,3),
            y = np.around(y_regular,3),
            color_continuous_scale = 'inferno',
            range_color = [np.nanmin(log_z[log_z != -np.inf]), log_z_interpolated.max()],
        )
        fig_q_vector.update_layout(
            title = 'RSM plot: Intensity (log-scale) vs Q-vectors',
            xaxis_title = 'Q_parallel (1/Å)',
            yaxis_title = 'Q_perpendicular (1/Å)',
            xaxis = dict(
                autorange = False,
                fixedrange = False,
                range = x_range,
            ),
            yaxis = dict(
                autorange = False,
                fixedrange = False,
                range = y_range,
            ),
            width = 600,
            height = 600,
        )
        json_q_vector = fig_q_vector.to_plotly_json()

        return json_2theta_omega, json_q_vector

    return json_2theta_omega, None
