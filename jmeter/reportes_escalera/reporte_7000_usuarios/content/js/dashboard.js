/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 13.197854498753493, "KoPercent": 86.8021455012465};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.0736194001662008, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "[GET] 03 - Filtrar y Paginar Vacantes"], "isController": false}, {"data": [0.995850622406639, 500, 1500, "[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)"], "isController": false}, {"data": [0.03248099516240498, 500, 1500, "[GET] 01 - Health Check"], "isController": false}, {"data": [0.04579252811026478, 500, 1500, "[GET] 02 - Listar Vacantes Generales"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 13237, 11490, 86.8021455012465, 5858.7245599456155, 96, 30120, 5005.0, 8668.0, 9631.0, 17538.01999999998, 435.3417088732487, 1359.0839518721634, 11.708151248931133], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["[GET] 03 - Filtrar y Paginar Vacantes", 247, 0, 0.0, 121.97975708502027, 103, 364, 116.0, 138.20000000000002, 150.6, 315.36000000000047, 34.045485871812545, 84.04979324603721, 6.981984407305307], "isController": false}, {"data": ["[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)", 241, 0, 0.0, 119.13692946058089, 96, 2573, 105.0, 119.80000000000001, 131.89999999999998, 264.71999999999707, 29.603242844859356, 9.308832222699914, 8.470459134320109], "isController": false}, {"data": ["[GET] 01 - Health Check", 7235, 6771, 93.58673116793365, 6505.002902557004, 96, 30120, 5543.0, 9289.0, 9822.2, 19353.28, 237.9464579359337, 674.7009803266625, 2.8463748931132016], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 5514, 4719, 85.58215451577802, 5518.570910409862, 105, 19959, 5005.0, 8135.5, 8736.25, 13500.700000000044, 234.72819377633988, 856.6593239831212, 6.3785648626069555], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 137, 1.1923411662315058, 1.034977713983531], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 6938, 60.382941688424715, 52.41368890231926], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4331, 37.693646649260224, 32.71889400921659], "isController": false}, {"data": ["Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 84, 0.7310704960835509, 0.6345848757271285], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 13237, 11490, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 6938, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4331, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 137, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 84, "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["[GET] 01 - Health Check", 7235, 6771, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 3620, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 3026, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 82, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 43, "", ""], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 5514, 4719, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 3912, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 711, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 94, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 2, "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
