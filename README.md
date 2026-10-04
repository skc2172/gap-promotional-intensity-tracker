## Gap Promotional Intensity Tracker

The Gap Promotional Intensity Tracker is a research prototype for tracking how broadly and deeply Gap discounts its online assortment over time.

The tracker collects advertised prices across four Gap apparel categories (men's jeans; men's T-shirts; women's jeans; women's T-shirts and tanks), measures promotional intensity at the product-color level, and presents the results in an interactive  dashboard via Streamlit. The goal is to turn publicly available pricing data into a repeatable signal that can be monitored alongside Gap's reported fundamentals.

## Methodology

The tracker measures:
- **Discount Breadth:** % of observed product-colors advertised below their reference price.
- **Median Discount Depth:** median discount among discounted product-colors.
- **Deep-Discount Share ≥30%:** % of product-colors discounted by at least 30%.

Each color is treated separately because Gap can advertise different prices for different colors of the same product.
The prototype covers Men's and Women's Jeans and T-Shirts. Denim was selected as a management-identified strong-performing category, while T-Shirts provide a comparison category for assessing whether promotional behavior in denim is category-specific or reflects a broader pattern across the assortment.

## Tools and Data

- **Python / Pandas** — data collection, normalization, validation, and metric calculation
- **Requests / Beautiful Soup** — web data collection and parsing
- **Wayback Machine** — supplemental historical observations
- **Streamlit / Plotly** — interactive dashboard and visualizations
- **Python unittest** — automated testing of calculations and parsing

## Running Locally

Requires Python 3.12+.

1. Clone the repository and navigate to the project directory.
2. Create a virtual environment:

   python3 -m venv .venv

3. Install dependencies:

   .venv/bin/python -m pip install -r requirements.txt

4. Launch the Streamlit dashboard:

   .venv/bin/python -m streamlit run app.py

5. Run the test suite:

   .venv/bin/python -m unittest discover -s tests -v

## Dashboard

The dashboard shows the current promotional picture, changes over time, category comparisons, and the underlying product-level evidence.

The "As of" date retrieves the latest validated observation available on or before a selected date. "Refresh Current Data" collects a new observation, while "Update Historical Archive" searches available Wayback Machine evidence. Not every snapshot is available on the Wayback Machine, so historical gaps are not interpolated.

## Historical Archive

Historical observations are reconstructed from available Wayback Archive snapshots where comparable pricing evidence can be validated. Historical observations are included only where sufficient pricing evidence is available; unavailable periods are left missing rather than estimated or interpolated.

The repository includes the curated data required by the dashboard, but certain supporting source evidence used during historical archive review is not bundled with the repository.

## Limitations

The tracker measures advertised online promotions, not realized transaction prices. The sample is not sales-weighted, covers only four categories, and can change as Gap's assortment changes. Historical archive coverage is also uneven, given limitations in Wayback coverage. 

Additionally, promotional activity alone cannot establish changes in demand, inventory, margins, or sales.

## Next Steps

The main next step would be to automate daily or weekly collection so the dataset builds consistently without requiring a manual refresh. With a longer history, I would evaluate whether sustained changes in promotional intensity precede changes in Gap's reported pricing, margins, inventory, or sales trends.