// ==UserScript==
// @name         RedFinPlus
// @namespace    http://tampermonkey.net/
// @version      0.2
// @description  Provide an external links for title reviews
// @author       info@alientech.software
// @updateURL    https://gist.githubusercontent.com/alientechsw/b69e11f5c7476b174d9f358f9fb7e713/raw/8bf903f6a7510604d4c38d91534c57c755d3b4fd/RedFinPlus.js
// @downloadURL  https://gist.githubusercontent.com/alientechsw/b69e11f5c7476b174d9f358f9fb7e713/raw/8bf903f6a7510604d4c38d91534c57c755d3b4fd/RedFinPlus.js
// @match        http*://www.redfin.com/*
// @include      /^https?:\/\/www.redfin.com\/.*\/[\d]+$/
// @grant        GM_*
// @grant        unsafeWindow
// @run-at       document-end
// @require      http://code.jquery.com/jquery-3.2.1.min.js

// ==/UserScript==
// devtools.chrome.enabled: true
// devtools.debugger.remote-enabled: true
var timer;

/*
I keep getting error:
[Report Only] Refused to connect to 'https://localhost:8000/JSONScoreByURL/WA/Bothell/17533-3rd-Ave-SE-98012/home/105199350' because it violates the following Content Security Policy directive: "connect-src 'self' https://www.redfin.com it-help.redfin.com https://p.tvpixel.com https://*.g.doubleclick.net *.google-analytics.com *.akamaihd.net https://*.facebook.com https://*.google.com".

XMLHttpRequest.send @ vendor.462f8a43638eefa56369.bundle.js:9

<meta http-equiv="content-type" content="text/html; charset=utf-8 ;">
<meta http-equiv="Content-Security-Policy" content="script-src 'self' http://onlineerp.solution.quebec 'unsafe-inline' 'unsafe-eval'; style-src 'self' maxcdn.bootstrapcdn.com">

*/

function httpGetAsync(theUrl, callback)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() {
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200){
            callback(xmlHttp.responseText);
        }
    }
    xmlHttp.open("GET", theUrl, true); // true for asynchronous
    xmlHttp.send(null);
};

function httpGet(theUrl)
{
    debugger;
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false ); // false for synchronous request
    xmlHttp.send( null );
    console.log("httpGet ("+theUrl+") = " + xmlHttp.responseText);

    return xmlHttp.responseText;
};

function CreateCORSRequest(method, url){
    var xhr = new XMLHttpRequest();
    if ("withCredentials" in xhr){
        xhr.open(method, url, true);
    } else if (typeof XDomainRequest != "undefined"){
        xhr = new XDomainRequest();
        xhr.open(method, url);
    } else {
        xhr = null;
    }
    return xhr;
};

function GetAddressParts(address_url) {
    //debugger;
    var myRegx = /http[s]?:\/\/www.redfin.com\/([\w]+)\/([\w-+]+)\/([\w-+]+)-([\d]+)?(\/(.*))?\/home\/([\d]+)/ig
    var res = myRegx.exec(address_url);
    console.log("address_parts = " + res);
    return {
        "state":res[1],
        "city":res[2],
        "display":res[3],
        "zip":res[4],
        "unit":res[6],
        "propertyId":res[7],
    };
};

function replaceAll(original_str, find_str, replace_str) {
  return original_str.split(find_str).join(replace_str);
};

function HandleHouse() {
    //debugger;
    console.log("detected a house url");
    var commentsSection = jQuery("[class*='CommentsSection']")[0];
    console.log("commentsSection = " + commentsSection.attributes[0].value);
    var parent = commentsSection.parentNode;

    var address_parts = GetAddressParts(location.href)

    var areavibes_sub_path = ""
    if (address_parts.display.length > 0) {
        areavibes_sub_path = replaceAll(address_parts.city, '-', '+') + "-" + address_parts.state + "/livability/";
    }
    var areavibes = document.createElement("DIV")
    areavibes.innerHTML = "<H2>Areavibes</H2><IFRAME width='100%' height='500' src='https://www.areavibes.com/" + areavibes_sub_path + "'/>"
    parent.appendChild(areavibes);

    var spotcrime_sub_path = ""
    if (address_parts.display.length > 0) {
        spotcrime_sub_path = "#"
            + replaceAll(address_parts.display, '-', '%20') + "%2C"
            + replaceAll(address_parts.city, '-', '%20') + "%2C"
            + address_parts.state + '%20' + address_parts.zip;
    }
    var spotcrime = document.createElement("DIV")
    spotcrime.innerHTML = "<H2>spotcrime</H2><IFRAME width='100%' height='500' src='https://spotcrime.com/"+spotcrime_sub_path+"'/>"
    parent.appendChild(spotcrime);

    var my_score = document.createElement("DIV");
    // Since my local server is http, it can't load inside the https://redfin without security exception
    // please turn on the "load dangerous script" see: https://groups.google.com/a/chromium.org/forum/#!topic/chromium-discuss/8QvDA6p3YoI
    my_score.innerHTML = "<A href='https://localhost:8000/HTMLScoreByURL" + location.pathname+"'><H2>My Score</H2></A><IFRAME width='100%' height='500' src='https://localhost:8000/HTMLScoreByURL" + location.pathname+"'/>";
    parent.appendChild(my_score);
};

var HandleFavoritesBusy = false
var enc = new TextDecoder("utf-8");

function HandleFavorites() {
    if(HandleFavoritesBusy){
        return;
    }
    HandleFavoritesBusy = true;

    // drag and drop code is inspired by https://www.html5rocks.com/en/tutorials/dnd/basics/
    // class : FavoritesHomeList
    //   class : FavoritesPageList
    //     class : FavoritesHome
    var favoriteHomes = document.querySelectorAll('.FavoritesHome');
    [].forEach.call(favoriteHomes, function(favoriteHome) {
        //debugger;
        favoriteHome.setAttribute("draggable", "true");
        favoriteHome.style.cursor='move';
        favoriteHome.style.border="thick solid #F0F0F0";
        /*
        */
        var children = favoriteHome.getElementsByTagName("iframe");
        if (children.length == 0) {
            //debugger;
            var link_children = favoriteHome.getElementsByTagName("a");
            var house_link = replaceAll(link_children[0].href, "https://www.redfin.com", "")

            var score_service_link = "https://localhost:8000/JSONScoreByURL" + house_link

            var my_score_node = document.createElement("A");
            my_score_node.href=score_service_link;
            my_score_node.innerText="loading ...";
            favoriteHome.appendChild(my_score_node);

            var my_score = document.createElement("IFRAME");
            my_score.src = score_service_link;
            my_score.style="width:0;height:0;border:0; border:none;"
            favoriteHome.appendChild(my_score);

            var xhr = new XMLHttpRequest();
            xhr.open('GET', score_service_link, true);
            xhr.responseType = 'arraybuffer';
            xhr.onload = function(e) {
                if (this.status == 200) {
                    var myBlob = this.response;
                    // myBlob is now the blob that the object URL pointed to.
                    //debugger;
                    var score_json_str = enc.decode(myBlob);
                    var score = JSON.parse(score_json_str);
                    //console.log(score_json_str);
                    my_score_node.innerText=score.value.value.toFixed(2);
                }
            };
            xhr.send();

            /*
            httpGetAsync(score_service_link, function(responseText){
                my_score_node.innerText=responseText.length;
            });
            */

            //debugger;
            /*
            var request = CreateCORSRequest('get', score_service_link);
            if(request){
                request.onload = function() {
                    debugger;
                    my_score_node.innerText=this.innerText;
                };
                //request.onreadystatechange = handler;
                request.send(null);
            }
            */

            /*
            var my_score = document.createElement("IFRAME");
            // my_score.outerHTML = '<iframe src="https://localhost:8000/JSONScoreByURL/WA/Bothell/17533-3rd-Ave-SE-98012/home/105199350" style="width:0;height:0;border:0; border:none;"/>';
            my_score.src = score_service_link;
            my_score.onload = function() {
                HandleFavoritesBusy.value = true;
                //debugger;

                //var y = (this.contentWindow || this.contentDocument);
                //if (y.document)y = y.document;

                //var response = eval(iframeWindow.jQery("#document"));
                //my_score_link.innerText=response.value.value;
                HandleFavoritesBusy.value = false;
            }
            favoriteHome.appendChild(my_score);
            */
        }
    });

    HandleFavoritesBusy = false;
};

function HandleList(){
    var favoritesHomeList = document.querySelectorAll('.favoritesPageLists');
    if(favoritesHomeList.length > 0) {
        favoritesHomeList[0].addEventListener("DOMNodeInserted",function(){
            //debugger;
            //timer = setTimeout(HandleFavorites, 5000);
            HandleFavorites();
        });
    }
}

(function() {
    'use strict';

    // check URL to see if it represents a house
    //debugger;
    if (/^https?:\/\/www.redfin.com\/.*\/[\d]+$/.test (location.href) ) {
        timer = setTimeout(HandleHouse, 5000);
    } else if (/^https?:\/\/www.redfin.com\/.*favorite.*$/ig.test (location.href)) {
        setTimeout(function(){
            setTimeout(HandleFavorites, 5000);
            var favoritesPageView = document.querySelectorAll('.FavoritesPageView');
            favoritesPageView[0].onchange = function(newFavoritesPageView) {
                HandleList();
            };
            HandleList();
        }, 1000);
    }
})();


