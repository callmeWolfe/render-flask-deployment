import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

data = pd.read_csv('/content/food_nutrition_dataset.csv')

data['Food_Item'] = data['Food_Item'].str.lower()

print(data.head())

food_items = data['Food_Item'].unique()
print("Unique Food Items in the Dataset:")
for item in food_items:
    print(item)

label_encoders = {}
categorical_cols = ['Food_Item', 'Food_Type']
for col in categorical_cols:
    le = LabelEncoder()
    data[col] = le.fit_transform(data[col])
    label_encoders[col] = le

X = data[['Food_Item', 'Grams']]
y = data['Protein']

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(random_state=42, n_estimators=100)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

food_item = 'paneer'
grams = 240

encoded_food_item = label_encoders['Food_Item'].transform([food_item])

new_sample = pd.DataFrame({
    'Food_Item': encoded_food_item,
    'Grams': [grams]
})

new_sample_scaled = scaler.transform(new_sample)

predicted_protein = model.predict(new_sample_scaled)
print(f"\nPredicted Protein Content for {food_item} ({grams}g): {predicted_protein[0]:.2f} grams")