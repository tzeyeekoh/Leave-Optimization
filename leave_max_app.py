import streamlit as st
import pandas as pd
import plotly.express as px

#CODE LOGIC

public_holidays = {
    "New Year's Day":'01-01-2024',
    "CNY Day 1":'02-10-2024',
    "CNY Day 2":'02-12-2024', #Falls on a Sunday, Mon is PH
    "Good Friday":'03-29-2024',
    "Hari Raya":'04-10-2024',
    "Labour Day":'05-01-2024',
    "Vesak Day":'05-22-2024',
    "Hari Raya Haji":'06-17-2024',
    "National Day":'08-09-2024',
    "Deepavali":'10-31-2024',
    "Christmas":'12-25-2024'
}

def preprocess_dates(from_date, to_date, holidays_dict):
    dates = pd.date_range(start=from_date, end=to_date, freq='D')
    df_year_dates = pd.DataFrame({
    'Date':dates,
    'Day of week':dates.day_of_week
    })
    
    df_year_dates['Weekend'] = (df_year_dates['Day of week']>=5).astype(int)
    df_year_dates['Public Holidays'] = df_year_dates['Date'].apply(lambda x: int(x in pd.to_datetime(list(holidays_dict.values()))))
    df_year_dates['Day Off'] = (df_year_dates[['Weekend','Public Holidays']].sum(axis=1)>0).astype(int)

    df_year_dates = df_year_dates.set_index('Date')

    return df_year_dates

def perm_consec_offs(calendar_days, no_leaves):
    permutations = []

    start = 0
    end = 1

    while start < len(calendar_days):
        while end < len(calendar_days)+1:
            leaves_used = (end-start)-sum(calendar_days[start:end])

            if leaves_used>no_leaves:
                start +=1
                end = start+1
                leaves_used = 0
            
            if leaves_used>0:
                permutations.append([calendar_days[start:end].index.date, leaves_used, (end-start)])
            end += 1
        start+=1
        end = start+1
            
    
    return pd.DataFrame(permutations, columns=['Days Off', 'Leaves Used', 'No. Days Off'])

def postprocess_leavedates(df_leave_perm):

    df_leave_perm['Days Off per Leave'] = df_leave_perm['No. Days Off']/df_leave_perm['Leaves Used']
    df_leave_perm['Start Date'] = df_leave_perm['Days Off'].apply(lambda x : x[0])
    df_leave_perm['End Date'] = df_leave_perm['Days Off'].apply(lambda x : x[-1])
    df_leave_perm['Days Off'] = df_leave_perm['Days Off'].apply(lambda x : [d.strftime('%a, %d %b %Y') for d in x])

    # Ignore permutations with no value proposition
    df_leave_perm = df_leave_perm.loc[df_leave_perm['Days Off per Leave']>1]
    # Remove permutations where there are greater consecutive days off with the same number of leaves taken 
    df_leave_perm = df_leave_perm.groupby(['Start Date', 'Leaves Used']).agg({'No. Days Off':'max', 'Days Off per Leave':'max', 'End Date':'max', 'Days Off':'max'})
    
    df_leave_perm = df_leave_perm.reset_index()
    df_leave_perm['Period'] = df_leave_perm['Days Off'].apply(lambda x: x[0]+' - '+x[-1])

    return df_leave_perm


# STREAMLIT APP

st.set_page_config(layout="wide")
st.title('Leave Maximization App')

leaves_avail = st.number_input('Leaves Available', min_value=0, max_value=365, value=21)

from_col, to_col = st.columns(2)
with from_col:
    range_start = st.date_input('From', value=pd.to_datetime("01-01-2024"))
with to_col:
    range_end = st.date_input('To:', value=pd.to_datetime("12-31-2024"))

leave_range = st.slider('Number of Consecutive Days off', 1,60, value=(5,20), step=1)

if st.button('Run Optimization'):
    st.subheader(('Top 100 ways to utilize '+str(leaves_avail)+' days of leave for '+str(leave_range[0])+' to '+str(leave_range[1])+' consecutive days off'),
                 divider='grey')
    print(range_start, range_end, leaves_avail)
    df_year_dates = preprocess_dates(range_start, range_end, public_holidays)
    df_leave_perm = perm_consec_offs(df_year_dates['Day Off'], leaves_avail)
    df_leave_perm = postprocess_leavedates(df_leave_perm)

    df_filtered_leaves = df_leave_perm.loc[((df_leave_perm['No. Days Off']>=leave_range[0]) & (df_leave_perm['No. Days Off']<=leave_range[1]))]
    df_filtered_leaves = df_filtered_leaves.sort_values(by='Days Off per Leave', ascending=False).head(100)


    fig = px.timeline(df_filtered_leaves.sort_values(by='Start Date', ascending=False), 
                      x_start="Start Date", 
                      x_end="End Date", 
                      y="Period", 
                      color='Days Off per Leave',
                      color_continuous_scale='reds',
                      text='No. Days Off',
                      
                      height=2500,
                      template='seaborn',
                      
                      hover_data=['Leaves Used', 'No. Days Off'])
    
    fig.update_traces(textangle=0)
    for key in public_holidays:
        fig.add_vline(x=pd.to_datetime(public_holidays[key]), line_dash='dash', line_width=1)
        fig.add_annotation(x=pd.to_datetime(public_holidays[key]), text=key, textangle=90, y=101, xshift=7, showarrow=False)
        
    st.plotly_chart(fig, theme=None, use_container_width=True)
