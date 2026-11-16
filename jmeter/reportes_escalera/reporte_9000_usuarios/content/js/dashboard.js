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

    var data = {"OkPercent": 13.110636694713047, "KoPercent": 86.88936330528695};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.07239733768680146, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "[GET] 03 - Filtrar y Paginar Vacantes"], "isController": false}, {"data": [1.0, 500, 1500, "[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)"], "isController": false}, {"data": [0.032325825650601006, 500, 1500, "[GET] 01 - Health Check"], "isController": false}, {"data": [0.043818235467689585, 500, 1500, "[GET] 02 - Listar Vacantes Generales"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 15926, 13838, 86.88936330528695, 5845.6370086650795, 95, 30293, 5005.0, 8604.300000000001, 9859.65, 19317.109999999997, 471.7137610331141, 1451.2480342637432, 12.59152995601564], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["[GET] 03 - Filtrar y Paginar Vacantes", 294, 0, 0.0, 121.42857142857147, 103, 356, 115.0, 137.0, 152.0, 305.05000000000047, 38.56749311294766, 95.21349862258953, 7.909349173553719], "isController": false}, {"data": ["[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)", 285, 0, 0.0, 109.30526315789469, 96, 339, 105.0, 119.0, 127.0, 164.4199999999979, 39.28325292901447, 12.352741643694005, 11.240227644727774], "isController": false}, {"data": ["[GET] 01 - Health Check", 8569, 7987, 93.20807562142608, 6381.421286031041, 95, 30293, 5006.0, 9158.0, 9927.5, 20398.699999999986, 260.77297626293364, 719.8212765805691, 3.3036104876749848], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 6778, 5851, 86.32339923281204, 5657.769843611685, 104, 25438, 5005.0, 7804.200000000001, 9855.0, 14931.500000000002, 219.26050528903698, 793.4615645116941, 5.651919044981076], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 157, 1.1345570169099581, 0.9858093683285194], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 8923, 64.48186154068507, 56.027878940097956], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4597, 33.22011851423616, 28.864749466281552], "isController": false}, {"data": ["Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 161, 1.1634629281688105, 1.0109255305789275], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 15926, 13838, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 8923, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4597, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 161, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 157, "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["[GET] 01 - Health Check", 8569, 7987, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 4223, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 3575, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 134, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 55, "", ""], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 6778, 5851, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 4700, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 1022, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 102, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 27, "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
