/*
Build fun little tables using Divs.
*/

// const { createApp, computed, ref } = Vue;

const TablesApp = createApp({
    mounted() {
        console.log('setup')
        this.loadDiff()
    }
    , data() {
        return {
            connections: []
            , startups: []
        }
    }
    , methods: {

        async loadDiff() {
            console.log('loadDiff')
            const response = await fetch("diff.json", { cache: "no-store" });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            let d = await response.json();
            console.log('Data', d)
            this.diffData = d
            let b = d.reports.compare.benchmark
            let doSort = true;
            let direction = 1
            this.connections = this.makeConnections(b.connections, doSort, 'value', direction)

            this.startups = this.makeStartups(b.startup, doSort, 'value', 0)

            this.throughput_64 = this.makeThroughput(b.throughput['64'], doSort, 'value', direction)
            this.throughput_1024 = this.makeThroughput(b.throughput['1024'], doSort, 'value', direction)
            this.throughput_16384 = this.makeThroughput(b.throughput['16384'], doSort, 'value', direction)

            this.latency_64 = this.makeLatency(b.latency['64'], doSort, 'value', direction)
            this.latency_1024 = this.makeLatency(b.latency['1024'], doSort, 'value', direction)

        }

        , makeLatency(items, sort = true, sortKey = 'value', inverse = false, label_key='rate'){
            let r = []
            let maxRate = 0
            let minRate = Infinity;
            let key = 'rate';

            for (let name in items) {
                let c = items[name]
                let value = c[key].b

                if (value < minRate) {
                    minRate = value
                }
                if (value > maxRate) {
                    maxRate = value
                }
                let me = name.startsWith('ps-')

                let label = value;
                if (label_key != undefined) {
                    label = c[label_key].b
                }
                r.push({
                    name, value, key, me, label
                })
            }

            let minPerc = (minRate / maxRate) * 100
            let performFloor = false;
            r.forEach((e) => {
                let floorVal = performFloor ? minPerc + 2: 0
                e.height = ((e.value / maxRate) * 100) - (floorVal)
            });

            if (!sort) return r;
            return this.sortInverse(r, sortKey, inverse)
        }

        , makeThroughput(items, sort=true, sortKey='value', inverse=false, label_key='rate'){
            let r = []
            let maxRate = 0
            let minRate = Infinity;
            let key = 'vs_best';

            for (let name in items) {
                let c = items[name]
                let value = c[key].b

                if (value < minRate) {
                    minRate = value
                }
                if (value > maxRate) {
                    maxRate = value
                }
                let me = name.startsWith('ps-')

                let label = value;
                if (label_key != undefined) {
                    label = c[label_key].b
                }
                r.push({
                    name, value, key, me, label
                })
            }

            let minPerc = (minRate / maxRate) * 100
            let performFloor = false;
            r.forEach((e) => {
                let floorVal = performFloor ? minPerc + 2: 0
                e.height = ((e.value / maxRate) * 100) - (floorVal)
            });

            if (!sort) return r;
            return this.sortInverse(r, sortKey, inverse)
        }


        , makeStartups(items, sort=true, sortKey='value', inverse=false, label_key='mean_ms'){
            let r = []
            let maxRate = 0
            let minRate = Infinity;
            let key = 'relative_to_fastest';

            for (let name in items) {
                let c = items[name]
                let value = c[key].b

                if (value < minRate) {
                    minRate = value
                }
                if (value > maxRate) {
                    maxRate = value
                }
                let me = name.startsWith('ps-')
                let label = c[label_key].b
                r.push({
                    name, value, key, me, label
                })
            }

            let minPerc = (minRate / maxRate) * 100
            let performFloor = false;
            r.forEach((e) => {
                let floorVal = performFloor ? minPerc + 2: 0
                e.height = ((e.value / maxRate) * 100) - (floorVal)
            });

            if (!sort) return r;
            return this.sortInverse(r, sortKey, inverse)
        }

        , sortInverse(r, sortKey, inverse = false) {

            r.sort(function(a, b) {
              var keyA = a[sortKey] // new Date(a[sortKey]),
                keyB = b[sortKey] // new Date(b[sortKey]);
              // Compare the 2 dates
              if (keyA < keyB) return -1;
              if (keyA > keyB) return 1;
              return 0;
            });

            if (inverse) {
                r.reverse()
            }
            return r
        }

        , makeConnections(conns, sort = true, sortKey = 'value', inverse = false) {
            let r = []
            let maxRate = 0
            let minRate = Infinity;
            let key = 'rate';
            for (let name in conns) {
                let c = conns[name]
                let value = c[key].b

                if (value < minRate) {
                    minRate = value
                }
                if (value > maxRate) {
                    maxRate = value
                }
                let me = name.startsWith('ps-')

                r.push({
                    name, value, key, me
                })
            }

            /* Calculate the height
                1. Calculate the min size
                2. for each;
                    the height (as percent),
                    minus the min percent,
                    plus some tiny padding

            This floors the percent across all - but is rough.
            */

            let minPerc = (minRate / maxRate) * 100
            let performFloor = false;
            r.forEach((e) => {
                let floorVal = performFloor ? minPerc + 2: 0
                e.height = ((e.value / maxRate) * 100) - (floorVal)
            });

            if (!sort) return r;
            return this.sortInverse(r, sortKey, inverse)
        }

    }
})

const  app = TablesApp.mount("#tables_app");
