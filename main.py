import pandas as pd
import geocoder
import requests
import googlemaps
import math
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from jinja2 import Template

# API 키 설정
google_maps_api_key = "AIzaSyCJxIsD-JpDpDYZxjZomy9Ccl0EjeDpK80"

# 사용자 위치 자동 가져오기
g = geocoder.ip('me')  # IP 주소를 기반으로 위치 가져오기
user_location = (g.latlng[0], g.latlng[1])  # (위도, 경도)
3TL2U4S5M4
# Haversine 거리 계산 함수
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 지구의 반지름 (킬로미터)
    dlat = radians(lat2 - lat1)
    dlon = radians(lat2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # 거리 반환

# 도보 시간 계산 함수 (Google Maps API 사용)
def calculate_walking_time(start, end):
    gmaps = googlemaps.Client(key=google_maps_api_key)
    directions_result = gmaps.directions(start, end, mode="walking")
    if directions_result and len(directions_result) > 0:
        walking_time_seconds = directions_result[0]['legs'][0]['duration']['value']
        return timedelta(seconds=walking_time_seconds)
    return timedelta(minutes=0)

# 목적지의 위도와 경도를 가져오는 함수 (Google Maps Geocoding API 사용)
def get_coordinates(location_input):
    gmaps = googlemaps.Client(key=google_maps_api_key)
    geocode_result = gmaps.geocode(location_input)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    return None

# 구글 맵 API를 사용하여 경로 계산
def get_route(start, end, departure_time=None):
    gmaps = googlemaps.Client(key=google_maps_api_key)
    if departure_time is None:
        departure_time = datetime.now()
    directions_result = gmaps.directions(start, end, mode="transit", departure_time=departure_time, language="ko")
    return directions_result

def create_html(start, destination, directions_result):
    template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>대중교통 경로</title>
        <script src="https://maps.googleapis.com/maps/api/js?key={{ google_maps_api_key }}&callback=initialize" async defer></script>
        <script type="text/javascript">
            // 전역 변수로 markers와 infowindows 배열 정의
            var markers = [];
            var infowindows = [];

            function initialize() {
                // markers와 infowindows 배열 초기화
                markers = [];
                infowindows = [];

                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(function(position) {
                        var userLat = position.coords.latitude;
                        var userLng = position.coords.longitude;
                        var mapOptions = {
                            zoom: 14,
                            center: new google.maps.LatLng(userLat, userLng)
                        };
                        var map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);

                        // 경로 표시 함수 호출
                        displayRoute(map, userLat, userLng, {{ destination[0] }}, {{ destination[1] }});
                    });
                } else {
                    alert("Geolocation is not supported by this browser.");
                }
            }

            function displayRoute(map, userLat, userLng, destLat, destLng) {
                var directionsService = new google.maps.DirectionsService();
                var directionsRenderer = new google.maps.DirectionsRenderer();
                directionsRenderer.setMap(map);

                var request = {
                    origin: new google.maps.LatLng(userLat, userLng),
                    destination: new google.maps.LatLng(destLat, destLng),
                    travelMode: 'TRANSIT'
                };

                directionsService.route(request, function(result, status) {
                    if (status == 'OK') {
                        directionsRenderer.setDirections(result);

                        var bounds = new google.maps.LatLngBounds();
                        bounds.extend(new google.maps.LatLng(userLat, userLng));
                        bounds.extend(new google.maps.LatLng(destLat, destLng));
                        map.fitBounds(bounds);

                        var steps = result.routes[0].legs[0].steps;
                        var myArrivalTime = new Date(); // 현재 시간을 Date 객체로 저장

                        var currentStepIndex = 0;
                        var stepInterval;

                        var userMarker = new google.maps.Marker({
                            position: new google.maps.LatLng(userLat, userLng),
                            map: map,
                            title: '내 위치',
                            icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
                        });

                        function moveToNextStep(waitForTransit = true) {
                            if (currentStepIndex >= steps.length) {
                                clearInterval(stepInterval);
                                return;
                            }

                            var step = steps[currentStepIndex];
                            var stepDuration = step.duration.value; // duration in seconds
                            var stepPath = step.path; // 경로의 각 지점 배열

                            var startTime = new Date().getTime();
                            var endTime = startTime + stepDuration * 1000;

                            var pathIndex = 0;
                            stepInterval = setInterval(function() {
                                var currentTime = new Date().getTime();
                                var progress = (currentTime - startTime) / (endTime - startTime);

                                if (progress >= 1) {
                                    clearInterval(stepInterval);
                                    userMarker.setPosition(step.end_location);

                                    // 정류소에 도착했을 때 남은 시간을 기다림
                                    if (waitForTransit && step.travel_mode === 'TRANSIT') {
                                        var arrivalTime = new Date(step.transit.arrival_time.value);
                                        var now = new Date();
                                        var waitTime = arrivalTime - now;

                                        if (waitTime > 0) {
                                            setTimeout(function() {
                                                currentStepIndex++;
                                                moveToNextStep();
                                            }, waitTime);
                                        } else {
                                            currentStepIndex++;
                                            moveToNextStep();
                                        }
                                    } else {
                                        currentStepIndex++;
                                        moveToNextStep();
                                    }

                                    // 구글맵 API 재조회하여 정보 업데이트
                                    updateTransitInfo(step.end_location, destLat, destLng, map);
                                } else {
                                    // 경로의 각 지점을 따라 마커를 이동
                                    var segmentProgress = progress * (stepPath.length - 1);
                                    var segmentIndex = Math.floor(segmentProgress);
                                    var segmentFraction = segmentProgress - segmentIndex;

                                    var startLatLng = stepPath[segmentIndex];
                                    var endLatLng = stepPath[segmentIndex + 1];

                                    var currentLat = startLatLng.lat() + (endLatLng.lat() - startLatLng.lat()) * segmentFraction;
                                    var currentLng = startLatLng.lng() + (endLatLng.lng() - startLatLng.lng()) * segmentFraction;

                                    userMarker.setPosition(new google.maps.LatLng(currentLat, currentLng));
                                }
                            }, 1000);
                        }

                        function updateTransitInfo(startLocation, destLat, destLng, map) {
                            var directionsService = new google.maps.DirectionsService();
                            var request = {
                                origin: startLocation,
                                destination: new google.maps.LatLng(destLat, destLng),
                                travelMode: 'TRANSIT'
                            };

                            directionsService.route(request, function(result, status) {
                                if (status == 'OK') {
                                    var steps = result.routes[0].legs[0].steps;
                                    var myArrivalTime = new Date(); // 현재 시간을 Date 객체로 저장

                                    // 기존 마커와 인포윈도우 제거
                                    markers.forEach(marker => marker.setMap(null));
                                    infowindows.forEach(infowindow => infowindow.close());
                                    markers = [];
                                    infowindows = [];

                                    for (var i = 0; i < steps.length; i++) {
                                        var step = steps[i];

                                        if (i > 0) {
                                            var prevStep = steps[i - 1];
                                            if (prevStep.travel_mode === 'WALKING') {
                                                var walkingTimeSeconds = prevStep.duration.value;
                                                myArrivalTime.setSeconds(myArrivalTime.getSeconds() + walkingTimeSeconds);
                                            } else if (prevStep.travel_mode === 'TRANSIT') {
                                                var prevTransitDetails = prevStep.transit;
                                                var prevArrivalTimeValue = prevTransitDetails.arrival_time.value;
                                                myArrivalTime = new Date(prevArrivalTimeValue);
                                            }
                                        }

                                        if (step.travel_mode === 'TRANSIT') {
                                            var transitDetails = step.transit;
                                            var stopLocation = transitDetails.departure_stop.location;
                                            var stopName = transitDetails.departure_stop.name;
                                            var arrivalTime = transitDetails.arrival_time.text;
                                            var departureTime = transitDetails.departure_time.text;
                                            var arrivalTimeValue = transitDetails.arrival_time.value;

                                            var myArrivalTimeFormatted = myArrivalTime.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

                                            // 새로운 마커와 인포윈도우 생성
                                            var stopMarker = new google.maps.Marker({
                                                position: stopLocation,
                                                map: map,
                                                title: stopName
                                            });
                                            markers.push(stopMarker);

                                            var infowindow = new google.maps.InfoWindow();
                                            infowindows.push(infowindow);

                                            var transitType = transitDetails.line.vehicle.type.toLowerCase();
                                            var transitTypeText = transitType === 'bus' ? '버스 도착 예정 시간' : '지하철 도착 예정 시간';

                                            var infowindowContent = '<b>정류소명:</b> ' + stopName + '<br>' +
                                                                    '<b>' + transitTypeText + ':</b> ' + departureTime + '<br>' +
                                                                    '<b>나의 도착 예정 시간:</b> ' + myArrivalTimeFormatted + '<br>' +
                                                                    '<b>대중교통 탑승 시간:</b> ' + step.duration.text + '<br>' +
                                                                    '<b>남은 시간:</b> <span id="remaining-time-' + i + '"></span>';

                                            infowindow.setContent(infowindowContent);
                                            infowindow.open(map, stopMarker);

                                            updateRemainingTime(arrivalTimeValue, 'remaining-time-' + i);

                                            // 카드 정보 업데이트
                                            var card = document.getElementById('card-' + i);
                                            if (card) {
                                                card.querySelector('h3').innerText = (transitDetails.line.vehicle.type === 'SUBWAY' ? '역명' : '정류소명') + ': ' + stopName;
                                                card.querySelector('p:nth-of-type(1)').innerText = transitTypeText + ': ' + departureTime;
                                                card.querySelector('p:nth-of-type(2)').innerText = '나의 도착 예정 시간: ' + myArrivalTimeFormatted;
                                                card.querySelector('p:nth-of-type(3)').innerText = '대중교통 탑승 시간: ' + step.duration.text;
                                                card.querySelector('span').id = 'remaining-time-card-' + i;

                                                // 남은 시간 업데이트
                                                updateRemainingTime(arrivalTimeValue, 'remaining-time-card-' + i);
                                            }
                                        }
                                    }

                                    // 최종 목적지 정보 업데이트
                                    var destinationMarker = new google.maps.Marker({
                                        position: new google.maps.LatLng(destLat, destLng),
                                        map: map,
                                        title: '최종 목적지'
                                    });
                                    markers.push(destinationMarker);

                                    var destinationInfowindow = new google.maps.InfoWindow();
                                    infowindows.push(destinationInfowindow);

                                    var destinationArrivalTimeFormatted = myArrivalTime.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

                                    var destinationInfowindowContent = '<b>최종 목적지</b><br>' +
                                                                    '<b>나의 도착 예정 시간:</b> ' + destinationArrivalTimeFormatted + '<br>' +
                                                                    '<b>남은 시간:</b> <span id="remaining-time-destination"></span>';

                                    destinationInfowindow.setContent(destinationInfowindowContent);
                                    destinationInfowindow.open(map, destinationMarker);

                                    updateRemainingTime(myArrivalTime.getTime(), 'remaining-time-destination');
                                } else {
                                    console.error('Directions request failed due to ' + status);
                                }
                            });
                        }


                        moveToNextStep();

                        // 카드 형식으로 HTML에 추가할 컨테이너 생성 (한 번만 생성)
                        var cardContainer = document.getElementById('card-container');
                        if (!cardContainer) {
                            cardContainer = document.createElement('div');
                            cardContainer.id = 'card-container';
                            document.body.appendChild(cardContainer);
                        } else {
                            cardContainer.innerHTML = ''; // 기존 카드 초기화
                        }

                        for (var i = 0; i < steps.length; i++) {
                            var step = steps[i];

                            if (i > 0) {
                                var prevStep = steps[i - 1];
                                if (prevStep.travel_mode === 'WALKING') {
                                    var walkingTimeSeconds = parseInt(prevStep.duration.text) * 60;
                                    myArrivalTime.setSeconds(myArrivalTime.getSeconds() + walkingTimeSeconds);
                                } else if (prevStep.travel_mode === 'TRANSIT') {
                                    var prevTransitDetails = prevStep.transit;
                                    var prevArrivalTimeValue = prevTransitDetails.departure_time.value;
                                    var transitDurationSeconds = parseInt(prevStep.duration.text) * 60;
                                    myArrivalTime = new Date(prevArrivalTimeValue);
                                    myArrivalTime.setSeconds(myArrivalTime.getSeconds() + transitDurationSeconds);
                                }
                            }

                            if (step.travel_mode === 'TRANSIT') {
                                var transitDetails = step.transit;
                                var stopLocation = transitDetails.departure_stop.location;
                                var stopName = transitDetails.departure_stop.name;
                                var arrivalTime = transitDetails.arrival_time.text;
                                var departureTime = transitDetails.departure_time.text;
                                var arrivalTimeValue = transitDetails.departure_time.value;

                                var myArrivalTimeFormatted = myArrivalTime.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

                                var stopMarker = new google.maps.Marker({
                                    position: stopLocation,
                                    map: map,
                                    title: stopName + ' (도착 예정: ' + arrivalTime + ')',
                                    icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                                });

                                var transitType = transitDetails.line.vehicle.type.toLowerCase();
                                var transitTypeText = transitType === 'bus' ? '버스 도착 예정 시간' : '지하철 도착 예정 시간';

                                var infowindowContent = '<b>정류소명:</b> ' + stopName + '<br>' +
                                                        '<b>' + transitTypeText + ':</b> ' + departureTime + '<br>' +
                                                        '<b>나의 도착 예정 시간:</b> ' + myArrivalTimeFormatted + '<br>' +
                                                        '<b>대중교통 탑승 시간:</b> ' + step.duration.text + '<br>' +
                                                        '<b>남은 시간:</b> <span id="remaining-time-' + i + '"></span>';

                                var infowindow = new google.maps.InfoWindow({
                                    content: infowindowContent
                                });

                                stopMarker.addListener('click', (function(marker, content) {
                                    return function() {
                                        infowindow.setContent(content);
                                        infowindow.open(map, marker);
                                    };
                                })(stopMarker, infowindow.content));

                                updateRemainingTime(arrivalTimeValue, 'remaining-time-' + i);

                                var stopName = transitDetails.departure_stop.name;
                                var stopType = transitDetails.line.vehicle.type === 'SUBWAY' ? '역명' : '정류소명';

                                // 카드 형식으로 HTML에 추가
                                var cardHtml = '<div class="card" id="card-' + i + '">' +
                                            '<h3>' + stopType + ': ' + stopName + '</h3>' +
                                            '<p>' + transitTypeText + ': ' + departureTime + '</p>' +
                                            '<p>나의 도착 예정 시간: ' + myArrivalTimeFormatted + '</p>' +
                                            '<p>대중교통 탑승 시간: ' + step.duration.text + '</p>' +
                                            '<p>남은 시간: <span id="remaining-time-card-' + i + '"></span></p>' +
                                            '<button onclick="handleBoarding(' + i + ', true)">탑승 성공</button>' +
                                            '<button onclick="handleBoarding(' + i + ', false)">탑승 실패</button>' +
                                            '</div>';
                                cardContainer.insertAdjacentHTML('beforeend', cardHtml);
                        
                                // 남은 시간 업데이트
                                updateRemainingTime(arrivalTimeValue, 'remaining-time-card-' + i);
                            }
                        }

                        // 최종 목적지에 마커 추가
                        var destinationMarker = new google.maps.Marker({
                            position: new google.maps.LatLng(destLat, destLng),
                            map: map,
                            title: '최종 목적지',
                            icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
                        });

                        var destinationArrivalTimeFormatted = myArrivalTime.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

                        var destinationInfowindowContent = '<b>최종 목적지</b><br>' +
                                                        '<b>나의 도착 예정 시간:</b> ' + destinationArrivalTimeFormatted + '<br>' +
                                                        '<b>남은 시간:</b> <span id="remaining-time-destination"></span>';

                        var destinationInfowindow = new google.maps.InfoWindow({
                            content: destinationInfowindowContent
                        });

                        destinationMarker.addListener('click', function() {
                            destinationInfowindow.open(map, destinationMarker);
                            updateRemainingTime(myArrivalTime.getTime(), 'remaining-time-destination');
                        });

                        // 최종 목적지 마커를 경로 탐색 마커보다 나중에 추가하여 위에 표시되도록 함
                        destinationMarker.setMap(map);

                        // 탑승 성공 시 호출되는 함수
                        function handleBoarding(stepIndex, success) {
                            var card = document.getElementById('card-' + stepIndex);
                            if (success) {
                                card.style.backgroundColor = 'lightgreen';
                                alert('탑승 성공!');

                                // 기존의 움직이는 마커 중지
                                clearInterval(stepInterval);

                                // 탑승 성공 시, 마커를 탑승 정류장 위치로 이동
                                var step = steps[stepIndex];
                                userMarker.setPosition(step.start_location);

                                // 다음 step의 정류장에서 출발하도록 설정
                                var nextStep = steps[stepIndex];
                                if (nextStep) {
                                    userMarker.setPosition(nextStep.start_location);
                                    currentStepIndex = stepIndex;
                                    moveToNextStep(false);
                                }

                                // 구글맵 API 재조회하여 정보 업데이트
                                updateTransitInfo(step.start_location, destLat, destLng, map);

                                // 다음 정류장의 도착 예정 시간 계산
                                var nextStep = steps[stepIndex + 1];
                                if (nextStep) {
                                    var nextArrivalTime = new Date();
                                    nextArrivalTime.setSeconds(nextArrivalTime.getSeconds() + nextStep.duration.value);

                                    var nextArrivalTimeFormatted = nextArrivalTime.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

                                    // 다음 정류장의 카드 정보 업데이트
                                    var nextCard = document.getElementById('card-' + (stepIndex + 1));
                                    if (nextCard) {
                                        nextCard.querySelector('p:nth-of-type(2)').innerText = '나의 도착 예정 시간: ' + nextArrivalTimeFormatted;
                                        updateRemainingTime(nextArrivalTime.getTime(), 'remaining-time-card-' + (stepIndex + 1));
                                    }
                                }

                                // 마커 클릭 시 이모티콘 변경
                                userMarker.addListener('click', function() {
                                    var isRunning = true;
                                    var runningEmojis = ['ﾍ( ´Д`)ﾉ', 'ﾉ( ﾟДﾟ)ﾍ'];
                                    var emojiIndex = 0;
                                    var infowindow = new google.maps.InfoWindow();
                                    var emojiInterval = setInterval(function() {
                                        if (!isRunning) {
                                            clearInterval(emojiInterval);
                                            infowindow.close();
                                            return;
                                        }
                                        var emoji = runningEmojis[emojiIndex];
                                        var infowindowContent = '<div style="font-size: 24px;">' + emoji + '</div>';
                                        infowindow.setContent(infowindowContent);
                                        infowindow.open(map, userMarker);
                                        emojiIndex = (emojiIndex + 1) % runningEmojis.length;
                                    }, 500); // 0.5초마다 이모티콘 변경

                                    setTimeout(function() {
                                        isRunning = false;
                                    }, 5000); // 5초 후 이모티콘 변경 중지
                                });
                            } else {
                                card.style.backgroundColor = 'lightcoral';
                                alert('탑승 실패!');
                            }
                        }

                        // handleBoarding 함수를 전역으로 노출
                        window.handleBoarding = handleBoarding;
                    } else {
                        console.error('Directions request failed due to ' + status);
                    }
                });
            }

            function updateRemainingTime(arrivalTime, elementId) {
                function update() {
                    var now = new Date();
                    var arrival = new Date(arrivalTime); // Unix timestamp를 Date 객체로 변환

                    // 시간차 계산 (밀리초)
                    var diff = arrival - now;

                    if (diff <= 0) {
                        var element = document.getElementById(elementId);
                        if (element) {
                            element.innerText = "도착";
                        }
                        return;
                    }

                    // 분과 초로 변환
                    var minutes = Math.floor(diff / (1000 * 60));
                    var seconds = Math.floor((diff % (1000 * 60)) / 1000);

                    var element = document.getElementById(elementId);
                    if (element) {
                        element.innerText = minutes + "분 " + seconds + "초";
                    }
                }

                // 즉시 한 번 실행하고 1초마다 업데이트
                update();
                return setInterval(update, 1000);
            }

            window.onload = initialize;
        </script>
    </head>
    <body>
        <h1>대중교통 경로</h1>
        <div id="map-canvas" style="width: 100%; height: 600px;"></div>
    </body>
    </html>
    """)

    html_content = template.render(
        google_maps_api_key=google_maps_api_key,
        destination=destination
    )

    with open('transit_route_map.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

# 메인 실행
if __name__ == "__main__":
    # 목적지 입력 받기
    destination_input = "한국금융연수원"  # 테스트용으로 '서울역'으로 설정

    # 출발지와 목적지의 위도와 경도를 가져오기
    start = user_location  # 자동으로 가져온 사용자 위치
    destination = get_coordinates(destination_input)

    if destination:
        directions_result = get_route(start, destination)  # 출발지와 목적지를 인자로 전달
        create_html(start, destination, directions_result)  # 경로와 함께 HTML 생성
        print("지도가 transit_route_map.html로 저장되었습니다. 웹 브라우저에서 열어보세요.")
    else:
        print("목적지를 찾을 수 없습니다.")