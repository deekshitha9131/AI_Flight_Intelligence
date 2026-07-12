# Prediction APIs

Base Path

/api/v1/predictions

---

## Predict Flight Price

POST /predict

Input

Origin

Destination

Airline

Travel Date

Booking Date

Stops

Cabin

Response

Predicted Price

Confidence Score

Recommendation

---

## Prediction History

GET /history

Returns previous predictions.

---

## Prediction Details

GET /{prediction_id}