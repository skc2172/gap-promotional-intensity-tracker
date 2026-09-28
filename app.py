"""Gap research monitor. Start with: streamlit run app.py"""

from urllib.parse import urlsplit
from datetime import date, datetime, timezone, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from gap_tracker.dashboard_data import (ROOT, MEASURES, evidence_rows, load_snapshots,
                                        metric_value, refresh_current, daily_snapshots, readable_time, as_of_snapshots, update_historical_archive)

st.set_page_config(page_title='Gap | Promotional Intensity Monitor', layout='wide')
st.markdown('### GAP / PROMOTIONAL INTENSITY MONITOR')
st.write("Monitor Gap's promotional intensity across categories and over time.")
st.caption('US advertised prices · Product-color observations · USD')

snapshots, errors = load_snapshots()
today = date.today()
earliest = min((datetime.fromisoformat(s['observed_at']).astimezone(timezone.utc).date() for s in snapshots), default=today)

with st.sidebar:
    st.header('Research controls')
    as_of = st.date_input('As of', value=today, min_value=min(earliest, today), max_value=today, key='as_of',
                          help='Latest available evidence through the selected UTC calendar day.')
    if as_of > today:
        st.error('As of cannot be after today.')
        st.stop()
    st.caption('Collect the latest Gap pricing observations and add them to the historical dataset.')
    if st.button('Refresh Current Data', type='primary'):
        with st.spinner('Collecting all reported pages, validating and calculating metrics…'):
            try:
                st.session_state['refresh_result'] = refresh_current()
            except Exception as exc:
                st.session_state['refresh_result'] = {'error': str(exc), 'returncode': 1}
    if 'refresh_result' in st.session_state:
        result = st.session_state['refresh_result']
        if result['returncode'] == 0:
            st.success('New snapshots saved. Views updated.')
        else:
            st.error('Refresh incomplete. Successful categories are available; previous snapshots are retained.')
        with st.expander('Refresh status'):
            for category, outcome in result.get('categories', {}).items():
                st.write(category.replace('-', ' ').title() + ': ' + outcome.get('status', 'Unavailable'))
            st.caption('Full refresh diagnostics are retained with the saved collection records.')

    with st.expander('Update Historical Archive'):
        st.caption('Search Wayback for additional historical observations. Archived coverage may be incomplete; not every category or period can be recovered.')
        start = st.date_input('Historical start date', value=today - timedelta(days=365), min_value=date(1996, 1, 1), max_value=today)
        end = st.date_input('Historical end date', value=today, min_value=date(1996, 1, 1), max_value=today)
        if st.button('Update Historical Archive', disabled=start > end):
            with st.spinner('Checking historical archive…'):
                try:
                    st.session_state['archive_result'] = update_historical_archive(start, end)
                except Exception:
                    st.session_state['archive_result'] = {'failed': True}
            st.rerun()
        if 'archive_result' in st.session_state:
            result = st.session_state['archive_result']
            if result.get('failed'):
                st.warning('Historical archive update could not complete. Saved observations are retained.')
            elif result.get('incomplete'):
                st.warning(f"Archive search could not be completed — {result['added']} new observations added. Saved observations are retained.")
            elif result['added']:
                st.success(f"Historical archive updated — {result['added']} new observations added.")
            else:
                st.info('Historical archive checked — no new valid observations found for this period.')

if 'refresh_result' in st.session_state or 'archive_result' in st.session_state:
    snapshots, errors = load_snapshots()
if errors:
    st.warning(f'{len(errors)} invalid snapshot(s) excluded. Saved evidence and validation records retain the details.')
if not snapshots:
    st.info('No validated metrics found. Use Refresh Current Data to collect the four categories.')
    st.stop()

categories = sorted({s['metrics']['category'] for s in snapshots})
selected = st.sidebar.multiselect('Categories', categories, default=categories)
if not selected:
    st.info('Select at least one category.')
    st.stop()
snapshots, resolved = as_of_snapshots(snapshots, as_of)
latest = {category: resolved[category] for category in selected if category in resolved}
focus = st.sidebar.selectbox('Focus category', selected)

def table_record(s):
    m = s['metrics']
    return {'Category': m['category'], **{label: metric_value(m, label) for label in MEASURES},
            'Observed UTC': s['observed_at'], 'Scope': s['scope'],
            'Observations': m['total_observations'], 'Styles': m['unique_styles_observed'],
            'Price coverage %': 100 * m['price_eligible_observations'] / m['total_observations']}

st.subheader('01 / ' + ('Current promotional picture' if as_of == today else 'Promotional picture as of ' + as_of.strftime('%b %d, %Y')))
st.write('See how widespread and how deep advertised discounts are' + (' today.' if as_of == today else ' as of the selected date.'))
st.caption('Latest available observations for each category. Collection dates are shown below.')
for col, category in zip(st.columns(len(selected)), selected):
    s = latest.get(category)
    with col:
        st.markdown('**' + category + '**')
        if s is None:
            st.write('Unavailable — no observation on or before this date.')
            continue
        for label in list(MEASURES)[:2]:
            value = metric_value(s['metrics'], label)
            st.metric(label, 'Unavailable' if value is None else f'{value:.1f}%')
        deep = metric_value(s['metrics'], 'Deep-Discount Share ≥30%')
        st.write(f'Deep-discount share ≥30%: **{deep:.1f}%**')
        st.caption('Collected ' + readable_time(s['observed_at']))
        if s['scope'] != 'All reported pages':
            st.caption('Historical' if s['metrics']['source'] == 'gap_wayback' else s['scope'])
with st.expander('Metric definitions'):
    st.markdown('**Discount Breadth** — Share of observed product/color combinations where the advertised current price is below the displayed reference price. Higher means discounting is more widespread.')
    st.markdown('**Median Discount Depth** — Median percentage price reduction among product/color combinations that are discounted. Higher means the typical discount is deeper.')
    st.markdown('**Deep-Discount Share ≥30%** — Share of observed product/color combinations discounted by at least 30%. Higher means substantial discounts are more widespread.')
    st.write('Different colors of the same product can have different advertised prices, so product/color combinations are measured separately.')

source_labels = {'All reported pages': 'Current', 'First page only': 'Current (partial sample)',
                 'Archive alternative': 'Historical', 'Archived API sample': 'Historical'}

st.subheader('02 / Change over time')
st.write('See how promotional activity has changed across historical and current observations.')
methodology = st.expander('Methodology & Data Quality')
with methodology:
    observation_types = st.multiselect('Snapshot scope', ['Current', 'Historical', 'Current (partial sample)'],
                                       default=['Current', 'Historical'])
    scopes = [scope for scope, label in source_labels.items() if label in observation_types]
    st.write('Historical observations are reconstructed from available archived Gap web data. Coverage varies by date and category and is not directly comparable to the current collection.')
    st.write('Observations do not represent a matched panel of the same products tracked continuously over time.')
    st.write('Missing periods are left unobserved rather than interpolated.')
    st.write("Price coverage refers to the availability of the required price fields within the observed sample, not coverage of Gap's full assortment.")

dates = sorted({s['metrics']['snapshot_date'] for s in snapshots})
if len(dates) > 1:
    period = st.select_slider('Observation date range', options=dates, value=(dates[0], dates[-1]),
                              format_func=lambda d: pd.Timestamp(d).strftime('%b %d, %Y'), key=f'period-{as_of}')
else:
    period = (dates[0], dates[0]) if dates else (None, None)
trend = [s for s in snapshots if s['metrics']['category'] in selected and s['scope'] in scopes
         and period[0] <= s['metrics']['snapshot_date'] <= period[1]]
st.caption('Historical and current samples are not directly comparable. Dots show available observations; gaps are not filled.')
trend = daily_snapshots(trend)
if len({s['metrics']['snapshot_date'] for s in trend if s['scope'] == 'All reported pages'}) == 1:
    st.info('Current collections cover only one day so far. Use historical observations as context, with the limitations explained in Methodology & Data Quality.')
measure = st.selectbox('Trend measure', list(MEASURES))
if trend:
    frame = pd.DataFrame([{**table_record(s), 'Date': s['metrics']['snapshot_date'], 'Observation type': source_labels[s['scope']]} for s in trend])
    chart = alt.Chart(frame).mark_point(size=100, filled=True).encode(
        x=alt.X('Date:T', title='Observation date', scale=alt.Scale(type='utc'), axis=alt.Axis(format='%b %d, %Y')),
        y=alt.Y(f'{measure}:Q', scale=alt.Scale(domain=[0, 100]), title=measure + ' (%)'),
        color=alt.Color('Category:N', scale=alt.Scale(domain=categories),
                        legend=alt.Legend(title='Category', orient='bottom', columns=2, labelLimit=0)),
        shape=alt.Shape('Observation type:N', legend=alt.Legend(title='Observation type', orient='bottom', labelLimit=0)), tooltip=['Category:N', alt.Tooltip('Date:T', title='Date', timeUnit='utcyearmonthdate', format='%b %d, %Y'), 'Observation type:N', alt.Tooltip(f'{measure}:Q', format='.1f')])
    st.altair_chart(chart, width='stretch')
else:
    st.info('No snapshots match these date and scope filters.')


st.subheader('03 / Category comparison')
st.write('Compare promotional activity across categories.')
st.caption('Same observations as Section 01. Actual observation dates may differ across categories; sample composition can differ.')
for category in selected:
    st.caption(category + ': ' + (readable_time(latest[category]['observed_at']) if category in latest else 'Unavailable'))
if latest:
    comparison = pd.DataFrame([table_record(s) for s in latest.values()])
    for col, label in zip(st.columns(3), MEASURES):
        with col:
            st.markdown('**' + label + '**')
            st.altair_chart(alt.Chart(comparison).mark_bar(color='#244c70').encode(
                y=alt.Y('Category:N', title=None, sort='-x', axis=alt.Axis(labelLimit=0)),
                x=alt.X(f'{label}:Q', title='%', scale=alt.Scale(domain=[0, 100])),
                tooltip=['Category', alt.Tooltip(f'{label}:Q', format='.1f')]).properties(height=170), width='stretch')
focus = st.selectbox('Investigate category', selected, index=selected.index(focus))

st.subheader('04 / Underlying evidence')
st.write('Inspect the products and advertised prices behind the aggregate metrics.')
choices = [s for s in reversed(snapshots) if s['metrics']['category'] == focus]
if not choices:
    st.info('Unavailable — no evidence for this category on or before the selected date.')
    st.stop()
evidence = st.selectbox('Evidence snapshot', choices, index=choices.index(latest[focus]), key=f'evidence-{as_of}-{focus}-{latest[focus]["id"]}',
                        format_func=lambda s: f"{readable_time(s['observed_at'])} · {source_labels[s['scope']]}")
m = evidence['metrics']; v = evidence['validation']
st.caption(f"{m['total_observations']:,} product-colors · {m['unique_styles_observed']:,} styles · "
           f"{100*m['price_eligible_observations']/m['total_observations']:.1f}% price coverage")
with st.expander('Discount distribution'):
    st.caption('Shows how observed product/color combinations are distributed across discount levels')
    bands = pd.DataFrame([{'Discount band': k, 'Observations': val['count']} for k, val in m['discount_bands'].items()])
    st.altair_chart(alt.Chart(bands).mark_bar(color='#254b70').encode(
        x=alt.X('Discount band:N', sort=list(m['discount_bands'])), y=alt.Y('Observations:Q', title='Observations'),
        tooltip=['Discount band', alt.Tooltip('Observations:Q', title='Product/colors')]).properties(height=180), width='stretch')
with methodology:
    st.write('Selected evidence snapshot: ' + focus + ' · ' + readable_time(evidence['observed_at']))

rows = pd.DataFrame(evidence_rows(evidence))
search = st.text_input('Find product, color or ID')
only_discounted = st.checkbox('Discounted observations only')
filtered = rows
if search:
    filtered = filtered[filtered[['Product', 'Color', 'Style ID', 'Product-color ID']].fillna('').astype(str)
                        .apply(lambda c: c.str.contains(search, case=False, regex=False)).any(axis=1)]
if only_discounted:
    filtered = filtered[filtered['Discount %'] > 0]
st.caption(f'{len(filtered)} of {len(rows)} observations shown. Filters do not recalculate snapshot KPIs. '
           'Blank fields mean unavailable. Promotional messages are shown separately from calculated discounts.')
research_fields = ['Product', 'Color', 'Reference price', 'Current price', 'Discount %', 'Promotional messaging', 'Product URL']
st.dataframe(filtered[research_fields], hide_index=True, width='stretch', column_config={
    'Reference price': st.column_config.NumberColumn(format='$%.2f'),
    'Current price': st.column_config.NumberColumn(format='$%.2f'),
    'Discount %': st.column_config.NumberColumn(format='%.1f%%'),
    'Product URL': st.column_config.LinkColumn(display_text='Gap product')})
st.download_button('Download visible evidence (CSV)', filtered.to_csv(index=False), 'gap-evidence.csv', 'text/csv')
with st.expander('Technical provenance'):
    historical = m['source'] == 'gap_wayback'
    st.write('Source: Archived Gap web data' if historical else 'Source: Gap public web data')
    source_row = evidence['rows'][0]
    source_url = (source_row.get('provenance', {}).get('evidence_url') if historical
                  else source_row.get('source_url'))
    parsed_url = urlsplit(source_url or '')
    if parsed_url.scheme in ('http', 'https') and parsed_url.hostname and (
            not historical or (parsed_url.hostname == 'web.archive.org' and parsed_url.path.startswith('/web/'))):
        st.link_button('View archived source' if historical else 'View source', source_url)
    st.write('Observation timestamp: ' + readable_time(evidence['observed_at']))
    st.write('Observation unit: product/color combination')
    st.write('Price basis: advertised current price versus displayed retailer reference price')
    coverage = {'All reported pages': 'All reported pages', 'First page only': 'First page only',
                'Archive alternative': 'Available archived sample', 'Archived API sample': 'Available archived sample'}
    st.write('Collection coverage: ' + coverage[evidence['scope']])
    pages = v.get('pages_collected')
    st.write('Pages collected: ' + (str(pages) if pages is not None else 'Not recorded'))
    st.write(f"Price coverage: {100*m['price_eligible_observations']/m['total_observations']:.1f}% of observed product/colors")
    st.caption('Full raw evidence, original source information and validation metadata are retained with the saved snapshot.')
