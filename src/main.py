""" 
Internal UI for OCF 
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime, timedelta

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.metric import MetricValue
from get_data import get_metric_value
from auth import check_password
from status import status_page

st.get_option("theme.primaryColor")

def get_x_y(metric_values):
    """
    Extra x and y values from the metric values

    x is the time
    y is the metric value
    """
    metric_values = [MetricValue.from_orm(value) for value in metric_values]
    # select data to show in the chart MAE and RMSE and date from the above date range
    x = [value.datetime_interval.start_datetime_utc for value in metric_values]
    y = [round(float(value.value), 2) for value in metric_values]

    return x, y


def get_recent_daily_values(values):
    """
    Get the recent daily values from the metric values
    """
    if len(values) == 0:
        day_before_yesterday = None
        yesterday = None
        today = None
    elif len(values) == 1:
        day_before_yesterday = None
        yesterday = None
        today = values[len(values) - 1]
    elif len(values) == 2:
        day_before_yesterday = None
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]
    else:
        day_before_yesterday = values[len(values) - 3]
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]

    return day_before_yesterday, yesterday, today


def metric_page():


    # set up title and subheader
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>', unsafe_allow_html=True
    )
    # set up sidebar
    st.sidebar.subheader("Select date range for charts")
    # select start and end date
    starttime = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=30))
    endtime = st.sidebar.date_input("End Date", datetime.today())

    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

    # set up database connection
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    # get metrics for comparing MAE and RMSE without forecast horizon

    with connection.get_session() as session:

        # read database metric values
        name_mae = "Daily Latest MAE"
        name_rmse = "Daily Latest RMSE"
        if use_adjuster:
            name_mae = "Daily Latest MAE with adjuster"
            name_rmse = "Daily Latest RMSE with adjuster"

        metric_values_mae = get_metric_value(
            session=session,
            name=name_mae,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
        )

        metric_values_rmse = get_metric_value(
            session=session,
            name=name_rmse,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
        )

        # transform SQL object into something readable
        x_mae, y_mae = get_x_y(metric_values=metric_values_mae)
        x_rmse, y_rmse = get_x_y(metric_values=metric_values_rmse)

        # getting recent statistics for the dashboard
        day_before_yesterday_mae, yesterday_mae, today_mae = get_recent_daily_values(values=y_mae)
        day_before_yesterday_rmse, yesterday_rmse, today_rmse = get_recent_daily_values(
            values=y_rmse
        )

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Metrics"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Recent MAE Values"):
        st.subheader("Recent MAE")
        t = datetime.today() - timedelta(days=1)
        t2 = datetime.today() - timedelta(days=2)
        t3 = datetime.today() - timedelta(days=3)
        col1, col2, col3 = st.columns([1, 1, 1])

        col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_mae)
        col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_mae)
        col3.metric(label=t.strftime("%d/%m/%y"), value=today_mae)

    with st.expander("Recent RMSE Values"):
        st.subheader("Recent RMSE")
        col1, col2, col3 = st.columns([1, 1, 1])
        col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_rmse)
        col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_rmse)
        col3.metric(label=t.strftime("%d/%m/%y"), value=today_rmse)

    df_mae = pd.DataFrame(
        {
            "MAE": y_mae,
            "datetime_utc": x_mae,
        }
    )

    df_rmse = pd.DataFrame(
        {
            "RMSE": y_rmse,
            "datetime_utc": x_rmse,
        }
    )

    st.sidebar.subheader("Select Forecast Horizon")
    forecast_horizon_selection = st.sidebar.multiselect(
        "Select", [60, 120, 180, 240, 300, 360, 420]
    )

    # set up title and subheader

    fig = px.bar(
        df_mae,
        x="datetime_utc",
        y="MAE",
        title="Nowcasting MAE",
        hover_data=["MAE"],
        color_discrete_sequence=["#FFAC5F"],
    )
    st.plotly_chart(fig, theme="streamlit")

    line_color = ['#9EC8FA', '#9AA1F9', '#FFAC5F', '#9F973A', '#7BCDF3', '#086788', '#63BCAF', '#4C9A8E']
    # MAE by forecast horizon adding go.Figure 
    fig2 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Nowcasting MAE by Forecast Horizon (see sidebar)"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MAE (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig2.add_trace(
            go.Scatter(
                x=df_mae["datetime_utc"],
                y=df_mae["MAE"],
                mode="lines",
                name="Daily Total MAE",
                line=dict(color='#FFD053'),
            )
    )
        

    with connection.get_session() as session:
        # read database metric values
        for forecast_horizon in forecast_horizon_selection:
            metric_values = get_metric_value(
                session=session,
                name=name_mae,
                gsp_id=0,
                forecast_horizon_minutes=forecast_horizon,
                start_datetime_utc=starttime,
                end_datetime_utc=endtime+timedelta(days=1),
            )
            metric_values = [MetricValue.from_orm(value) for value in metric_values]
            x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
            y_mae_horizon = [round(float(value.value), 2) for value in metric_values]

            df = pd.DataFrame(
                {
                    "MAE": y_mae_horizon,
                    "datetime_utc": x_mae_horizon,
                }
            )

            fig2.add_traces(
                [
                    go.Scatter(
                        x=df["datetime_utc"],
                        y=df["MAE"],
                        name=f"{forecast_horizon}-minute horizon",
                        mode="lines",
                        line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                    )
                ]
            )

    
    # fig2 = px.line(
    #     df_mae,
    #     x="datetime_utc",
    #     y="MAE",
    #     title="MAE Nowcasting Forecast",
    #     hover_data=["MAE"],
    #     color_discrete_sequence=["#FFD053"],
    # )

    # with connection.get_session() as session:
    #     # read database metric values
    #     for forecast_horizon in forecast_horizon_selection:
    #         metric_values = get_metric_value(
    #             session=session,
    #             name=name_mae,
    #             gsp_id=0,
    #             forecast_horizon_minutes=forecast_horizon,
    #             start_datetime_utc=starttime,
    #             end_datetime_utc=endtime,
    #         )
    #         metric_values = [MetricValue.from_orm(value) for value in metric_values]
    #         x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
    #         y_mae_horizon = [round(float(value.value), 2) for value in metric_values]

    #         df = pd.DataFrame(
    #             {
    #                 "MAE": y_mae_horizon,
    #                 "datetime_utc": x_mae_horizon,
    #             }
    #         )
    #         fig2.add_traces(
    #             [
    #                 go.Scatter(
    #                     x=df["datetime_utc"],
    #                     y=df["MAE"],
    #                     name=f"{forecast_horizon}-minute horizon",
    #                 )
    #             ]
    #         )

        st.plotly_chart(fig2, theme="streamlit")

    # add chart with forecast horizons on x-axis
    # # customize color scale for chart
    # fig_forecast_horizon = px.scatter(
    fig_forecast_horizon = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Nowcasting MAE by Date and Forecast Horizon"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="MAE (MW)")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Date")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    with connection.get_session() as session:
        # read database metric values
        for forecast_horizon in forecast_horizon_selection:
                metric_values = get_metric_value(
                    session=session,
                    name=name_mae,
                    gsp_id=0,
                    forecast_horizon_minutes=forecast_horizon,
                    start_datetime_utc=starttime,
                    end_datetime_utc=endtime+timedelta(days=1),
            )
                metric_values = [MetricValue.from_orm(value) for value in metric_values]
                x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
                y_mae_horizon = [round(float(value.value), 2) for value in metric_values]
                # forecast_horizon = [value.forecast_horizon_minutes for value in metric_values]

                df_mae_horizon = pd.DataFrame(
                    {
                    "MAE": y_mae_horizon,
                    "datetime_utc": x_mae_horizon,
                    }
                )
           
                fig_forecast_horizon.add_traces(
                    [
                        go.Scatter(
                            x=df_mae_horizon["MAE"],
                            y=df_mae_horizon["datetime_utc"],
                            name=f"{forecast_horizon}-minute horizon",
                            mode="markers",
                            line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                        )
                    ]
                )
            
        st.plotly_chart(fig_forecast_horizon, theme="streamlit")

    # comparing MAE and RMSE
    fig3 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Nowcasting MAE with RMSE for Comparison"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig3.add_traces(
        [
            go.Scatter(
                x=df_mae["datetime_utc"],
                y=df_mae["MAE"],
                name="MAE",
                mode="lines",
                line=dict(color='#FFD053'),
            ),
            go.Scatter(
                x=df_rmse["datetime_utc"],
                y=df_rmse["RMSE"],
                name="RMSE",
                mode="lines",
                line=dict(color=line_color[0]),
            ),
        ]
    )

    st.plotly_chart(fig3, theme="streamlit")

    st.subheader("Raw Data")
    col1, col2 = st.columns([1, 1])
    col1.write(df_mae)
    col2.write(df_rmse)


if check_password():
    page_names_to_funcs = {
        "Metrics": metric_page,
        "Status": status_page,
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys())
    page_names_to_funcs[demo_name]()