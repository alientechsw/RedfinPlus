# Redfin data download

Redfin APIs are `REST`. There are many endpoints, but they use almost the same parameters. I reverse engineered those from the redfin web bage itself. If you look at the page you will find a `<SCRIPT>` section that show the endpoint called and the arguments used.

I've removed some specefics from the samples for privacy resons. you will need to replace these missing parts to make the samples work

**Acknoledgment**
- This documentation is an updated version of [gomoto/house/REDFIN.md](https://github.com/gomoto/house/blob/master/REDFIN.md)
- This work is also ispired with [althor880/househunt](https://github.com/althor880/househunt)

## APIs end points

### 1. gis / gis-csv search

```
https://www.redfin.com/stingray/do/gis-search?
https://www.redfin.com/stingray/api/gis?
https://www.redfin.com/stingray/api/gis-csv?
```

### 2. Initial Info
Initial info is specially important because it give you the `listingId`
```
http://www.redfin.com/stingray/api/home/details/initialInfo?path=[REPLACE with redfin house URL (no http://www.redfin.com)]
```

### 3. Images
```
https://www.redfin.com/stingray/api/home/details/aboveTheFold
```

### 4. Amenities and History
```
https://www.redfin.com/stingray/api/home/details/belowTheFold

https://www.redfin.com/stingray/api/home/details/belowTheFold?propertyId=[REPLACE]&accessLevel=1&listingId=[REPLACE]
```

## 5. aggregate-trends

**Looking for medianSalePerSqFt average for KingCounty region=118, type=5**
```
https://www.redfin.com/stingray/api/region/5/118/99/aggregate-trends
```

**for zip 98008**
```
https://www.redfin.com/stingray/api/region/2/40749/1/aggregate-trends
https://www.redfin.com/stingray/api/region/2/40749/1/trends
https://www.redfin.com/stingray/api/region?al=1&clustering_threshold=350&ep=true&lpp=20&mpt=1&num_homes=350&page_number=1&region_id=98008&region_type=2&start=0&tz=true&v=8
```

### Other APIs that are left undocumented
```
https://www.redfin.com/stingray/api/home/details/neighborhoodStats/statsInfo?propertyId=[REPLACE]&accessLevel=3&type=json

https://www.redfin.com/stingray/api/home/details/mainHouseInfoPanelInfo

https://www.redfin.com/stingray/api/home/details/avmHistoricalData?propertyId=[REPLACE]&accessLevel=3&type=json

http://www.redfin.com/stingray/api/home/details/commute/commuteInfo?listingId=[REPLACE]&propertyId=[REPLACE]&accessLevel=3

```

## Parameters

### region type

id | type
---|---
1|neighborhood
2|ZIP code
5|County
6|City

### Property type
```
uipt=1
```

id | type
---|---
1|House
2|Condo
3|Townhouse
4|Multi-family
5|Land
6|Other

### Status
```
status=1
```

id | status
---|---
1|active
130|pending
131|active + pending

### Order
```
ord=redfin-recommended-asc
```

### Unknown
```
al=3
page_number=1
sp=true
v=8
```

Assume these are required.

### Listing type
```
sf=1,3,7
```

id | type
---|---
1,7|Agent-listed homes (includes Redfin listings)
2|MLS-Listed Foreclosures
3|For sale by owner
4|Foreclosures
5,6|New construction

### Days on market
Reverse range, inclusive.
Please note that relisting sometime cases reset of this number. `RedfinPlus` will go back in property history to correct this issue

```
Less than 3:
time_on_market_range=3-

which is shorthand for
time_on_market_range=3-0

More than 7:
time_on_market_range=-7

1-3 days, inclusive:
time_on_market_range=3-1
```

### Price
```
min_price=50000
max_price=850000
```

### Beds
```
num_beds=4
max_num_beds=6
```

### Baths (min)
```
num_baths=3.25
max_num_baths=4
```

### Year
```
min_year_built=1995
max_year_built=2015
```

### Square footage
```
min_listing_approx_size=500
max_listing_approx_size=1750
```

### Lot size
```
min_parcel_size=2000
max_parcel_size=43560
```

### Stories
```
min_stories=1
max_stories=3
```

### Garage
```
gar=true
min_num_park=2
```

### Basement
```
basement=true
```

### HOA
```
hoa=0
```

### Limit number of results
```
num_homes=350
```

### propertyId and listingId
Once the search returns, you need both the `propertyId`, and `listingId` to call the **details** endpoints.
If you use only the `propertyId` you could lose all or most of the details. The good news is `initialInfo` end point can return the `listingId` given the property URL.

# Examples

**King County**
```
cluster_bounds=-122.93818%2046.92567%2C-119.89496%2046.92567%2C-119.89496%2048.13656%2C-122.93818%2048.13656%2C-122.93818%2046.92567
market=seattle
region_id=118
region_type=5
zoomLevel=9
```

**Bothell, WA**

```
https://www.redfin.com/stingray/do/gis-search?status=1&render=json&region_id=29439&uipt=1&sp=true&al=3&lpp=50&region_type=6&mpt=99&page_number=1&v=8&no_outline=false&num_homes=500&min_price=500000&max_price=760000&min_num_beds=3&min_num_baths=2&min_stories=2&gar=true&min_num_park=2


ZIP: 98011
98012
98021
98041
```


**2 regions**
```
https://www.redfin.com/stingray/do/gis-search?region_id=2&region_id=118&render=json&min_listing_approx_size=2250&min_num_park=2&al=3&min_num_baths=2&market=seattle&min_year_built=2000&min_num_beds=3&min_price=500000&page_number=1&status=1&uipt=1&min_stories=2&gar=True&region_type=5&mpt=99&num_homes=500&sp=True&lpp=50&time_on_market_range=30-&v=8&no_outline=False&max_price=700000
```

**User Ploygon**
```
https://www.redfin.com/stingray/do/gis-search?status=1&region_id=2&region_id=118&render=json&min_listing_approx_size=1500&min_num_park=2&al=3&gar=True&mpt=99&min_num_baths=2&user_poly=-122.231519+47.601857,-122.09419+47.601857,-122.083891+47.602783,-122.074964+47.609727,-122.067411+47.620373,-122.065351+47.630092,-122.065351+47.648136,-122.073591+47.668023,-122.072904+47.691138,-122.077024+47.705926,-122.068098+47.721172,-122.068784+47.732719,-122.074277+47.749343,-122.071531+47.764576,-122.071531+47.776575,-122.077024+47.783035,-122.085264+47.789494,-122.08801+47.794568,-122.088697+47.799642,-122.09213+47.804254,-122.101057+47.810249,-122.107236+47.817627,-122.116163+47.821315,-122.182767+47.840215,-122.19856+47.84298,-122.252805+47.848971,-122.287138+47.848971,-122.292631+47.847588,-122.296751+47.844362,-122.300184+47.839293,-122.302244+47.832379,-122.306364+47.812094,-122.309797+47.803331,-122.309797+47.789494,-122.30705+47.775652,-122.303617+47.765037,-122.294691+47.749804,-122.277525+47.731796,-122.267912+47.715629,-122.247999+47.690214,-122.240446+47.686053,-122.233579+47.678657,-122.232893+47.673109,-122.239072+47.661549,-122.241132+47.650911,-122.248685+47.639346,-122.250059+47.634719,-122.250745+47.611116,-122.245252+47.60695,-122.231519+47.601857&num_homes=3000&market=seattle&uipt=1&uipt=3&sp=True&lpp=50&min_num_beds=3&min_price=500000&page_number=1&time_on_market_range=&v=8&region_type=5&region_type=5&max_price=700000
```

## External useful websites

**walk score**
```
https://www.walkscore.com/score/[REPLACE with `+` escaped address]/lat=[REPLACE]/lng=[REPLACE]?utm_source=redfin
```

**Area Vibes**
```
https://www.areavibes.com/Bothell-WA/livability/
```

**Spot Crime**
```
https://spotcrime.com/#[REPLACE with `URL escaped` address]
```
