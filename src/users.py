import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.read.read_user import (
    get_all_last_api_request,
    get_api_requests_for_one_user,
)
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection
from pvsite_datamodel.read.user import get_all_last_api_request as get_all_last_api_request_sites
from pvsite_datamodel.read.user import get_api_requests_for_one_user as get_api_requests_for_one_user_sites

from plots.users import make_api_requests_plot, make_api_frequency_requests_plot


def user_page():

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"API Users Page"}</h1>',
        unsafe_allow_html=True,
    )

    st.text("See which users have been using the API")

    start_time = st.sidebar.date_input(
        "Start Date",
        min_value=datetime.today() - timedelta(days=365),
        max_value=datetime.today(),
        value=datetime.today() - timedelta(days=31),
    )
    end_time = st.sidebar.date_input(
        "End Date",
        min_value=datetime.today() - timedelta(days=365),
        max_value=datetime.today() + timedelta(days=1),
        value=datetime.today() + timedelta(days=1),
    )

    # get last call from the database
    db_url = os.getenv("DB_URL", None)
    db_url_sites = os.getenv("SITES_DB_URL", None)

    # if both databases are available, let the user choose which one to use
    # if none, show error
    if db_url is not None and db_url_sites is not None:
        db_connection = st.sidebar.selectbox("Select", ['National', 'Sites'], index=0)
    elif db_url is not None:
        db_connection = 'National'
    elif db_url_sites is not None:
        db_connection = 'Sites'
    else:
        st.error("No database URL found")
        return

    # depending on which database has been selected, we choose the
    # 1. connection function
    # 2. get_all_last_api_request function
    # 3. get_api_requests_for_one_user function
    if db_connection == 'National':
        connection = DatabaseConnection(url=db_url, echo=True)
        get_all_last_api_request_func = get_all_last_api_request
        get_api_requests_for_one_user_func = get_api_requests_for_one_user
    else:
        connection = SitesDatabaseConnection(url=db_url_sites, echo=True)
        get_all_last_api_request_func = get_all_last_api_request_sites
        get_api_requests_for_one_user_func = get_api_requests_for_one_user_sites

    with connection.get_session() as session:

        last_requests_sql = get_all_last_api_request_func(session=session)

        last_request = [
            (last_request_sql.user.email, last_request_sql.created_utc)
            for last_request_sql in last_requests_sql
        ]

    last_request = pd.DataFrame(last_request, columns=["email", "last API request"])
    last_request = last_request.sort_values(by="last API request", ascending=False)
    last_request.set_index("email", inplace=True)

    st.write(last_request)

    # add selectbox for users
    email_selected = st.sidebar.selectbox("Select", last_request.index.tolist(), index=0)

    # get all calls for selected user
    with connection.get_session() as session:
        api_requests_sql = get_api_requests_for_one_user_func(
            session=session, email=email_selected, start_datetime=start_time, end_datetime=end_time
        )

        api_requests = [
            (api_request_sql.created_utc, api_request_sql.url)
            for api_request_sql in api_requests_sql
        ]
    api_requests = pd.DataFrame(api_requests, columns=["created_utc", "url"])

    fig = make_api_requests_plot(api_requests, email_selected, end_time, start_time)
    st.plotly_chart(fig, theme="streamlit")

    # add plot that shows amount of api calls per day
    api_requests["created_utc"] = pd.to_datetime(api_requests["created_utc"])
    api_requests["date"] = api_requests["created_utc"].dt.date
    api_requests_days = api_requests[['date','url']].groupby("date").count()
    api_requests_days.reset_index(inplace=True)

    print(api_requests_days)

    fig = make_api_frequency_requests_plot(api_requests_days, email_selected, end_time, start_time)
    st.plotly_chart(fig, theme="streamlit")

