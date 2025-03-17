from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
import json

from collections import defaultdict
from itertools import combinations

app = FastAPI()

# Load listings from JSON file
with open("listings.json", "r") as f:
    LISTINGS = json.load(f)

class VehicleRequest(BaseModel):
    length: int = Field(..., gt=0, description="Length must be a positive integer greater than 0")
    quantity: int = Field(..., gt=0, description="Length must be a positive integer greater than 0")
    width: int = 10

@app.post("/")
async def find_storage_spots(vehicles: List[VehicleRequest]):
    """
    Finds possible storage locations for the given vehicles, sorted by ascending cost.
    """
    try:
        # Process input and find valid storage combinations
        result = search_optimal_storage(vehicles, LISTINGS)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def search_optimal_storage(vehicles: List[VehicleRequest], listings: List[Dict]):
    """
    Implements the search and optimization logic.
    """
    storage_options = defaultdict(list)
    storage_options_expanded = defaultdict(list)

    # create dict with location as key
    # add lisitings to that location if they can fit any of the cars requested
    min_vehicle_length = min(vehicle.length for vehicle in vehicles)  # Find the smallest vehicle

    for listing in listings:
        if listing["length"] >= min_vehicle_length and listing["width"] >= 10:
            storage_options[listing["location_id"]].append(listing)

    results = []
    total_requested_space = sum(v.length * v.quantity * v.width for v in vehicles)

    # loop through the locations with potential to store all the cars
    for location_id, available_listings in storage_options.items():
        min_price = float("inf")
        best_combination = []

        # Try all combinations of listings
        # Need to try different numbers of combinations becasue we are assuming a listing
        # can fit more than one car if it has enough space
        for r in range(1, len(available_listings) + 1):
            for combo in combinations(available_listings, r):
                total_price = sum(l["price_in_cents"] for l in combo)
                total_available_space = sum(l["length"] * l["width"] for l in combo)

                # Dont check if total space is less than requested
                if total_available_space < total_requested_space:
                    continue

                # Dont check if already more expensive than current best
                if total_price >= min_price:
                    continue  

                if can_fit_all_vehicles(combo, vehicles):  # Now check exact fit
                    min_price = total_price
                    best_combination = combo

        if best_combination:
            results.append({
                "location_id": location_id,
                "listing_ids": [l["id"] for l in best_combination],
                "total_price_in_cents": min_price
            })

    # Sort by price
    return sorted(results, key=lambda x: x["total_price_in_cents"])

def can_fit_all_vehicles(combo, vehicles):
    """
    Checks if a combination of listings can fit all requested vehicles efficiently.
    Exits early if remaining space is too small for any vehicle.
    """
    remaining_vehicles = {v.length: v.quantity for v in vehicles}
    min_vehicle_length = min(remaining_vehicles.keys())  # Get the smallest vehicle length

    # break up any listings with space for more vehicles of width 10
    # into their own listing - so we only keep track of length in the comparisons
    # e.g if the width of the listing is 20 and length 30 storage_options_expanded
    # would include 2 listings of length 30
    combo_updated_by_width = []
    for listing in combo:
        additional_space_by_width = listing["width"] // 10
        #additional_space_by_width = 2
        for i in range(additional_space_by_width):
            combo_updated_by_width.append(listing)

    for listing in combo_updated_by_width:
        available_length = listing["length"]
        # Continue if no vehicle can fit
        if available_length < min_vehicle_length:
            continue
        # Try to fit vehicles, largest first (greedy)
        for length in sorted(remaining_vehicles.keys(), reverse=True):
            if remaining_vehicles[length] > 0 and available_length >= length:
                max_fit = available_length // length  # Max number that could fit
                used_count = min(remaining_vehicles[length], max_fit)  # Only use what’s needed

                remaining_vehicles[length] -= used_count
                available_length -= used_count * length

    return all(qty == 0 for qty in remaining_vehicles.values())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
