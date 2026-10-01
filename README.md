# Gap Promotional Intensity Tracker

The Gap Promotional Intensity Tracker is a research prototype for tracking how broadly and deeply Gap discounts its online assortment over time.

The tracker collects advertised prices across four Gap apparel categories (men's jeans; men's T-shirts; women's jeans; women's T-shirts and tanks), measures promotional intensity at the product-color level, and presents the results in an interactive  dashboard via Streamlit. The goal is to turn publicly available pricing data into a repeatable signal that can be monitored alongside Gap's reported fundamentals.

## Methodology

The tracker measures:
- Discount Breadth: % of observed product-colors advertised below their reference price.
- Median Discount Depth: median discount among discounted product-colors.
- Deep-Discount Share ≥30%: % of product-colors discounted by at least 30%.

Each color is treated separately because Gap can advertise different prices for different colors of the same product.
The prototype covers Men's and Women's Jeans and T-Shirts. Denim was selected as a management-identified strong-performing category, while T-Shirts provide a comparison with a category that has not been similarly highlighted.

## Current Findings

The main difference across categories is breadth rather than depth. Median discount depth is approximately 51% across all four categories, while discount breadth varies considerably. Nearly every observed denim product-color is currently discounted, compared with lower breadth in T-Shirts.

One snapshot cannot determine whether this is temporary or persistent, so observations are saved over time.

### Dashboard

The dashboard shows the current promotional picture, changes over time, category comparisons, and the underlying product-level evidence.

The "As of" date retrieves the latest validated observation available on or before a selected date. "Refresh Current Data" collects a new observation, while "Update Historical Archive" searches available Wayback Machine evidence. Not every snapshot is available on the Wayback Machine, so historical gaps are not interpolated.

### Limitations

The tracker measures advertised online promotions, not realized transaction prices. The sample is not sales-weighted, covers only four categories, and can change as Gap's assortment changes. Historical archive coverage is also uneven, given limitations in Wayback coverage. 

Additionally, promotional activity alone cannot establish changes in demand, inventory, margins, or sales.

### Next Steps

The main next step would be to automate daily or weekly collection so the dataset builds consistently without requiring a manual refresh. With a longer history, I would test whether changes in promotional intensity have any relationship with subsequent reported performance.