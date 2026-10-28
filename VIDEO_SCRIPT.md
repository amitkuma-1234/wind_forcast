# Video script (about 10 minutes)

Speak at a steady pace (about 130 words a minute). Items in [SQUARE BRACKETS] are numbers you must read off the
**real-data** dashboard before recording. Do not record on synthetic data and do not invent figures.

---

## PART 1: Client pitch (about 5 minutes)

**[0:00 | Dashboard open on the 30-minute view]**
Good morning. Every day before the day-ahead auction closes, your desk has to answer one question: how much power do we
buy from thermal plants, given what the wind will deliver tomorrow? Wind forecasts decide that number, and until now
there has been no easy way to see which forecast you actually had in hand, or how much to trust it.

This portal answers both questions, using only public Elexon data for Great Britain, for January 2026.

**[0:50 | Point at the cutoff selector]**
First, the forecast you could actually have used. Elexon publishes new wind forecasts many times a day. For each half-hour
of delivery day, the portal picks the latest forecast published before your decision time on the day before. Here that is
09:00, ahead of the morning auction close. Forecasts published later are never used, so nothing in this analysis uses
information you would not have had.

**[1:40 | KPI cards]**
Second, how good was that forecast. In January the average miss was [MAE] megawatts. The typical large miss, the
ninetieth percentile, was [P90] megawatts. The forecast ran [BIAS%] on average, which means it [over/under]-estimated wind
generation. In plain terms: when you buy thermal power to cover the gap, it is wise to keep a buffer of around [X] MW.

**[2:30 | Change the cutoff to 17:00, then back to 09:00]**
Watch what happens when I move the cutoff later. The error falls from [MAE at 09:00] to [MAE at 17:00] megawatts, because
newer forecasts are better. The value of waiting is visible and measurable, and the trade-off is that the auction has
already closed.

**[3:10 | Chart, then hourly error panel]**
The chart overlays actual and forecast wind, with the miss as bars underneath. Drag the slider to zoom into any storm. The
panel on the right shows the forecast is weakest around [HOURS], so those are the hours where extra caution pays off.

**[3:50 | Daily toggle, then table and CSV]**
Switch to daily totals for a quick view of which days surprised us. Every number is in the table, searchable by date, and
one click exports the CSV for your own models.

**[4:25 | Risk card]**
Finally, the risk card. Enter your own imbalance price and it converts forecast error into an exposure figure in pounds.
Treat it as a sizing tool, not a market forecast.

**[4:50 | Close]**
In short: you see the forecast you had, you know how wrong it tends to be, and you can size your buffers on evidence.
Thank you, and I would be happy to take questions.

---

## PART 2: Tech lead walkthrough (about 5 minutes)

**[0:00 | Repo tree]**
This is the technical review. The stack is FastAPI with pandas for the backend, React with Vite, Tailwind and Recharts for
the frontend, and Docker Compose for local runs. I used an AI assistant to draft the code, and I have reviewed it and written
tests for the core logic. That is disclosed in the README.

**[0:40 | elexon_service.py: loading]**
Data loading has three tiers: a CSV cache, then the live Elexon API, then a clearly flagged synthetic fallback so the UI never
breaks. The live fetch is chunked by date, filters FUELHH to wind, and cleans WINDFOR: it parses UTC timestamps, drops duplicates
and discards anything published after its own target period started.

**[1:40 | align()]**
This is the heart of the project. For every forecast row I compute the cutoff timestamp: the delivery day's midnight, minus
one day, plus the chosen time. I keep rows published at or before that cutoff, sort by publish time, and take the last row per
target start time. Then I inner-join to actuals. Error is actual minus forecast. The tests prove four things: it picks the
latest eligible forecast, a later cutoff sees newer forecasts, same-day forecasts are never used, and periods with no eligible
forecast are dropped instead of guessed.

**[2:40 | compute_metrics()]**
MAE and RMSE are standard. Bias is signed: positive means over-forecast. The risk score is a transparent heuristic, normalised
RMSE scaled so 50 percent equals 100, and the pounds exposure is just absolute error in megawatt-hours times a user price.
They are labelled illustrative in the UI because they are not market standards. Energy uses the median time step, so it stays
correct if the forecast is hourly.

**[3:20 | main.py]**
One analysis endpoint returns KPIs, the series, histogram and hour-of-day profile. Query parameters are validated with
patterns, so January dates only, and a start after the end returns a 422. Aligned frames are cached per cutoff. There is a CSV
export endpoint and a refresh endpoint.

**[3:55 | Frontend]**
App.jsx owns the filter state and calls the API with cancellation, so stale responses are ignored. Four components render
the output: KPICards, ForecastChart, ErrorMetricsChart and DataTable. A banner appears whenever data is synthetic.

**[4:20 | Docker and deploy]**
Docker Compose runs the API and an nginx container that serves the build and proxies slash-api. On Vercel, api/index.py exposes
the same FastAPI app and the committed CSV cache is bundled, so the deployed app never calls Elexon during a request.

**[4:45 | Close]**
Limitations: I wrote the Elexon queries from the documentation, the gate-closure time should be confirmed with the exchange,
and a next step would be forecast-horizon analysis and a probabilistic buffer recommendation. Thanks for reviewing.
