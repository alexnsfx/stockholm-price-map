import argh
import requests
from time import sleep
from math import ceil

# From https://www.svenskfast.se/kampanj/mellan-tummen-och-pekfingret/priskarta/
API_BASEPATH = "https://www.svenskfast.se/api/v1/mtop"

CSV_SEP = ","
CSV_EOL = "\n"

def empty_response():
    return {
        "WeightPrice": 0,
        "WeightSqr": 0,
        "Price": 0,
        "PriceSqr": 0,
        "Hits": 0,
        "PointsForSqrPriceInterval": 0,
        "PointsForPriceInterval": 0,
        "PointsForZoom": 0,
        "PointsForDays": 0,
        "PointsForHits": 0,
        "PointsForDistance": 0,
        "SumPointsPrice": 0,
        "SumPointsSqr": 0
    }


def fetch_area_data(top_left, bottom_right, housing_type, surface):
    """
        Fetch real estate data for an area.
        top_left: tuple (latitude, longitude) in decimal degree format
        bottom_right: tuple (latitude, longitude) in decimal degree format
        housing_type: str, "Lägenhet" or "Hus"
        surface: int, housing surface in square meters
    """
    endpoint = f"{top_left[0]},{top_left[1]},{bottom_right[0]},{bottom_right[1]}/{housing_type}/{surface}"

    r = requests.get(f"{API_BASEPATH}/{endpoint}")
    if r.status_code != 200:
        return empty_response()

    try:
        data = r.json()
        data.pop("Estates", None)
        return data
    except ValueError:
        return empty_response()


def get_area_bounds(top_left, box_height, box_width):
    """Returns (top_left, bottom_right)."""
    return top_left, (top_left[0] - box_height, top_left[1] + box_width)


def define_areas(start_top_left, end_bottom_right, resolution_lat, resolution_lon):
    """Generates all areas between start_top_left and end_bottom_right."""
    cursor = start_top_left

    # scan from north to south
    while cursor[0] > end_bottom_right[0]:
        # scan from west to east
        while cursor[1] < end_bottom_right[1]:
            area_top_left, area_bottom_right = get_area_bounds(cursor, resolution_lat, resolution_lon)
            yield area_top_left, area_bottom_right

            # move cursor to the east
            cursor = cursor[0], cursor[1] + resolution_lon

        # move cursor south and reset its longitude 
        cursor = cursor[0] - resolution_lat, start_top_left[1]

def fetch_map_data(areas, housing_type, surface, sleep_time):
    for area_top_left, area_bottom_right in areas:
        area_data = fetch_area_data(area_top_left, area_bottom_right, housing_type, surface)
        area_data["TopLeftLat"], area_data["TopLeftLon"] = area_top_left
        area_data["BottomRightLat"], area_data["BottomRightLon"] = area_bottom_right
        yield area_data

        # chill with the public API
        sleep(sleep_time)

def ordered_csv_headers():
    # dict order is preserved in python 3.7
    headers = [key for key in empty_response()]
    headers = ["TopLeftLat", "TopLeftLon", "BottomRightLat", "BottomRightLon", *headers]
    return headers

def to_csv_row(area_data):
    headers = ordered_csv_headers()
    values = [str(area_data[key]) for key in headers]
    row = CSV_SEP.join(values)
    return f"{row}{CSV_EOL}"

def main(
    start_top_left=(59.415335, 17.868951),
    end_bottom_right=(59.240899, 18.190988),
    resolution_lat=0.02,  # decimal degrees
    resolution_lon=0.02,  # decimal degrees
    housing_type="Lägenhet",
    surface_sqm=50,
    sleep_time_secs=0.1,
    dst_name="out.csv",
    verbose=False
):
    areas = define_areas(start_top_left, end_bottom_right, resolution_lat, resolution_lon)

    if verbose:
        # prepare progress bar
        num_tiles_lat = ceil((start_top_left[0] - end_bottom_right[0]) / resolution_lat)
        num_tiles_lon = ceil((end_bottom_right[1] - start_top_left[1]) / resolution_lon)
        total_tiles = num_tiles_lat * num_tiles_lon
        current_tile = 1

    with open(dst_name, "w") as output_file:
        headers = ordered_csv_headers()
        headers_row = f"{CSV_SEP.join(headers)}{CSV_EOL}"
        output_file.write(headers_row)

        map_data = fetch_map_data(areas, housing_type, surface_sqm, sleep_time_secs)
        for area_data in map_data:
            if verbose:
                print(f"Saving data for area {current_tile}/{total_tiles}: ({area_data['TopLeftLat']}, {area_data['TopLeftLon']}), ({area_data['BottomRightLat']}, {area_data['BottomRightLon']})")
                current_tile += 1

            row = to_csv_row(area_data)
            output_file.write(row)

if __name__ == '__main__':
    argh.dispatch_command(main)
