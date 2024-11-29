import pandas as pd
import numpy as np
import torch
from torch import nn, optim
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

# Load the dataset
data = pd.read_csv("Austria_data_2016-2019.csv")

# Preprocess the data for one particular day (e.g., "2017-06-15")
fixed_date = '2017-06-15'
data['utc_timestamp'] = pd.to_datetime(data['utc_timestamp'])
day_data = data[data['utc_timestamp'].dt.date == pd.to_datetime(fixed_date).date()]

# Validate solar and wind column names
if 'solar' not in day_data.columns or 'wind' not in day_data.columns:
    raise KeyError("The columns 'solar' and 'wind' do not exist in the dataset. Check the column names.")

solar_data = day_data['solar'].values
wind_data = day_data['wind'].values

# Normalize the solar and wind data (for GAN)
scaler = MinMaxScaler()
solar_data_scaled = scaler.fit_transform(solar_data.reshape(-1, 1)).flatten()
wind_data_scaled = scaler.fit_transform(wind_data.reshape(-1, 1)).flatten()

# Combine solar and wind data into a single array
input_data = np.stack((solar_data_scaled, wind_data_scaled), axis=1)

# Convert to PyTorch tensors
input_tensor = torch.tensor(input_data, dtype=torch.float32)

# Define the Generator (G) and Discriminator (D) for CIWGAN

class Generator(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(Generator, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, output_dim)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class Discriminator(nn.Module):
    def __init__(self, input_dim):
        super(Discriminator, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# Initialize the generator and discriminator
generator = Generator(input_dim=2, output_dim=2)  # 2 for solar and wind
discriminator = Discriminator(input_dim=2)

# Wasserstein GAN Loss and Optimizers
def wasserstein_loss(y_true, y_pred):
    return torch.mean(y_true * y_pred)

# Optimizers
optimizer_g = optim.RMSprop(generator.parameters(), lr=0.00005)
optimizer_d = optim.RMSprop(discriminator.parameters(), lr=0.00005)

# Training the GAN
def train_gan(data, generator, discriminator, optimizer_g, optimizer_d, epochs=5000, batch_size=64):
    for epoch in range(epochs):
        for i in range(0, len(data), batch_size):
            batch_data = data[i:i+batch_size]
            real_data = torch.tensor(batch_data, dtype=torch.float32).clone().detach()

            # Create labels dynamically based on batch size
            real_labels = torch.ones(real_data.size(0), 1)
            fake_labels = torch.zeros(real_data.size(0), 1)

            # Train Discriminator
            optimizer_d.zero_grad()

            real_preds = discriminator(real_data)
            real_loss = wasserstein_loss(real_labels, real_preds)

            noise = torch.randn(real_data.size(0), 2)
            fake_data = generator(noise)

            fake_preds = discriminator(fake_data)
            fake_loss = wasserstein_loss(fake_labels, fake_preds)

            d_loss = real_loss + fake_loss
            d_loss.backward()
            optimizer_d.step()

            # Train Generator
            optimizer_g.zero_grad()

            noise = torch.randn(real_data.size(0), 2)
            fake_data = generator(noise)
            fake_preds = discriminator(fake_data)

            g_loss = wasserstein_loss(real_labels, fake_preds)
            g_loss.backward()
            optimizer_g.step()

        if epoch % 500 == 0:
            print(f'Epoch [{epoch}/{epochs}], D Loss: {d_loss.item()}, G Loss: {g_loss.item()}')

    return generator, discriminator

# Train the model
trained_generator, trained_discriminator = train_gan(input_tensor, generator, discriminator, optimizer_g, optimizer_d)

# Step 1: Generate 1000 Scenarios
num_scenarios = 1000
noise = torch.randn(num_scenarios, 2)
generated_scenarios = trained_generator(noise).detach().numpy()

# Inverse scale back the generated scenarios to the original scale
generated_scenarios_original_scale = scaler.inverse_transform(generated_scenarios)

# Define the max and min values for pg_init
pg_max_solar = 50.0
pg_min_solar = 0.0
pg_max_wind = 70.0
pg_min_wind = 0.0

# Ensure the generated values are scattered between pg_min and pg_max for each generator
generated_scenarios_original_scale[:, 0] = np.random.uniform(pg_min_solar, pg_max_solar, num_scenarios)  # Solar between 0 and 50 MW
generated_scenarios_original_scale[:, 1] = np.random.uniform(pg_min_wind, pg_max_wind, num_scenarios)  # Wind between 0 and 70 MW

# Step 2: Save the Generated Scenarios to generated_scenarios.dat
output_file = "generated_scenarios.dat"
with open(output_file, 'w') as f:
    f.write("# Scenario Table for Solar and Wind Generation\n")
    f.write("param: GEN:   Gen_busNumber Gen_id  Gen_isInSvc  Gen_pgInit Gen_pgMax Gen_pgMin Gen_energyRamp Gen_spinRamp Gen_costCurveFlag pg_init :=\n")
    for i in range(num_scenarios):
        solar_gen, wind_gen = generated_scenarios_original_scale[i]
        f.write(f"8 'SOLAR_GEN' 10  1  {solar_gen:.2f}  50.0   0.0  1.0  5.5  1  {solar_gen:.2f}\n")
        f.write(f"9 'WIND_GEN' 3   1  {wind_gen:.2f}  70.0   0.0  2.0  10.0 1  {wind_gen:.2f}\n")
    f.write(";\n")

print(f"Generated scenarios have been saved to {output_file}")

# Step 3: Reduce the 1000 Scenarios to 25 using KMeans Clustering
kmeans = KMeans(n_clusters=25, random_state=42)
kmeans.fit(generated_scenarios_original_scale)

# Get the cluster centers (the reduced scenarios)
reduced_scenarios = kmeans.cluster_centers_

# Step 4: Save each reduced scenario into a separate .dat file
for i, scenario in enumerate(reduced_scenarios):
    reduced_output_file = f"reduced_scenario_{i+1}.dat"
    with open(reduced_output_file, 'w') as f:
        f.write("# Reduced Scenario for Solar and Wind Generation\n")
        f.write("param: GEN:   Gen_busNumber Gen_id  Gen_isInSvc  Gen_pgInit Gen_pgMax Gen_pgMin Gen_energyRamp Gen_spinRamp Gen_costCurveFlag pg_init :=\n")
        solar_gen, wind_gen = scenario
        f.write(f"8 'SOLAR_GEN' 10  1  {solar_gen:.2f}  50.0   0.0  1.0  5.5  1  {solar_gen:.2f}\n")
        f.write(f"9 'WIND_GEN' 3   1  {wind_gen:.2f}  70.0   0.0  2.0  10.0 1  {wind_gen:.2f}\n")
        f.write(";\n")

    print(f"Reduced scenario {i+1} has been saved to {reduced_output_file}")
