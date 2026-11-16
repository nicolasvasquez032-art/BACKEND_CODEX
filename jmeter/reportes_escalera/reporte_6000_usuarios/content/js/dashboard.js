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

    var data = {"OkPercent": 18.6783927706955, "KoPercent": 81.3216072293045};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.11997740842343069, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "[GET] 03 - Filtrar y Paginar Vacantes"], "isController": false}, {"data": [0.9972602739726028, 500, 1500, "[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)"], "isController": false}, {"data": [0.055424342623208944, 500, 1500, "[GET] 01 - Health Check"], "isController": false}, {"data": [0.07380143450358626, 500, 1500, "[GET] 02 - Listar Vacantes Generales"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 12394, 10079, 81.3216072293045, 5688.47724705499, 97, 31192, 5005.0, 9041.0, 9620.25, 17427.199999999997, 390.1901523737564, 1256.2022971170193, 15.021765746993452], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["[GET] 03 - Filtrar y Paginar Vacantes", 380, 0, 0.0, 160.88157894736855, 105, 429, 150.0, 234.4000000000002, 268.84999999999997, 356.03999999999996, 35.57386257255195, 87.82297322598764, 7.295421035386632], "isController": false}, {"data": ["[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)", 365, 0, 0.0, 143.5315068493153, 99, 2901, 126.0, 181.40000000000003, 222.09999999999997, 308.0, 34.77515243902439, 10.844905201981707, 9.950312172494282], "isController": false}, {"data": ["[GET] 01 - Health Check", 6351, 5775, 90.93056211620217, 6403.387025665258, 97, 31192, 5640.0, 9330.2, 9697.4, 19732.919999999987, 202.08737709612754, 562.1339793907309, 3.418636840932956], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 5298, 4304, 81.23820309550774, 5609.956964892411, 107, 21868, 5005.0, 8892.0, 9350.05, 13507.240000000005, 179.87980850847111, 719.2432713242284, 6.36083601415815], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 104, 1.0318483976584978, 0.8391157011457157], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 5578, 55.3427919436452, 45.00564789414233], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4313, 42.7919436452029, 34.799096336937225], "isController": false}, {"data": ["Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 84, 0.8334160134934021, 0.6777472970792319], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 12394, 10079, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 5578, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4313, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 104, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 84, "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["[GET] 01 - Health Check", 6351, 5775, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 3261, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 2420, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 80, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 14, "", ""], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 5298, 4304, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 3158, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 1052, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 90, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 4, "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
