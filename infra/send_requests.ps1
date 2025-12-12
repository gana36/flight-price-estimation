$airlines = @("Vistara", "AirAsia", "Indigo", "SpiceJet", "GO_FIRST", "Air_India")
$routes = @(
    @{source="Delhi"; dest="Mumbai"},
    @{source="Bangalore"; dest="Delhi"},
    @{source="Kolkata"; dest="Bangalore"},
    @{source="Mumbai"; dest="Hyderabad"},
    @{source="Chennai"; dest="Kolkata"}
)
$times = @("Early_Morning", "Morning", "Afternoon", "Evening", "Night", "Late_Night")
$stops = @("zero", "one", "two_or_more")
$classes = @("Economy", "Business")

for ($i=1; $i -le 100; $i++) {
    $airline = $airlines | Get-Random
    $route = $routes | Get-Random
    $depTime = $times | Get-Random
    $arrTime = $times | Get-Random
    $stop = $stops | Get-Random
    $class = $classes | Get-Random
    $duration = [math]::Round((Get-Random -Minimum 1.5 -Maximum 10.0), 2)
    $daysLeft = Get-Random -Minimum 1 -Maximum 50

    $body = @{
        airline = $airline
        flight = "$airline-$(Get-Random -Minimum 100 -Maximum 999)"
        source_city = $route.source
        departure_time = $depTime
        stops = $stop
        arrival_time = $arrTime
        destination_city = $route.dest
        class = $class
        duration = $duration
        days_left = $daysLeft
    } | ConvertTo-Json

    Invoke-RestMethod -Uri "http://localhost:8000/predict" -Method Post -ContentType "application/json" -Body $body | Out-Null

    Write-Host "Request $i sent"
    Start-Sleep -Milliseconds 100
}