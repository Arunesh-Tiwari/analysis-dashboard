import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.api import UserSQL, APIRequestSQL

from plots.users import make_api_requests_plot


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
        "End Date", min_value=datetime.today() - timedelta(days=365), max_value=datetime.today()
    )

    # get last call from the database
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:

        last_requests_sql = (
            session.query(APIRequestSQL)
            .distinct(APIRequestSQL.user_uuid)
            .join(UserSQL)
            .order_by(APIRequestSQL.user_uuid, APIRequestSQL.created_utc.desc())
            .all()
        )

        last_request = [
            (last_request_sql.user.email, last_request_sql.created_utc)
            for last_request_sql in last_requests_sql
        ]

    last_request = pd.DataFrame(last_request, columns=["email", "last API reuqest"])
    last_request = last_request.sort_values(by="last API reuqest", ascending=False)
    last_request.set_index("email", inplace=True)

    st.write(last_request)

    # add selectbox for users
    email_selected = st.sidebar.selectbox("Select", last_request.index.tolist(), index=0)

    # get all calls for selected user
    with connection.get_session() as session:
        api_requests_sql = (
            session.query(APIRequestSQL)
            .join(UserSQL)
            .where(UserSQL.email == email_selected)
            .where(APIRequestSQL.created_utc >= start_time)
            .where(APIRequestSQL.created_utc <= end_time)
            .all()
        )

        api_requests = [
            (api_request_sql.created_utc, api_request_sql.url)
            for api_request_sql in api_requests_sql
        ]
    api_requests = pd.DataFrame(api_requests, columns=["created_utc", "url"])

    fig = make_api_requests_plot(api_requests, email_selected, end_time, start_time)
    st.plotly_chart(fig, theme="streamlit")


