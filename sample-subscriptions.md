# Sample Subscriptions

Here are some sample subscriptions that can be used:

## Named Interface `in-octets`

```
python ncc-establish-subscription.py --host=127.0.0.1 --port=2223 -u vagrant -p vagrant \
    --period=1000 \
    --xpath '/interfaces/interface[name="GigabitEthernet1"]/statistics/in-octets'
```

## Two Subscriptions On Named Interface, `in-octets` and `out-octets`

```
python ncc-establish-subscription.py --host=127.0.0.1 --port=2223 -u vagrant -p vagrant \
    --period=1000 \
    --xpath \
        '/interfaces/interface[name="GigabitEthernet1"]/statistics/in-octets' \
        '/interfaces/interface[name="GigabitEthernet1"]/statistics/out-octets'
```

## Memory Statistics

```
python ncc-establish-subscription.py --host=127.0.0.1 --port=2223 -u vagrant -p vagrant \
    --period=1000 \
    --xpath '/memory-statistics'
```

## Memeory Statistics, Named Component

```
python ncc-establish-subscription.py --host=127.0.0.1 --port=2223 -u vagrant -p vagrant \
    --period=1000 \
    --xpath '/memory-statistics/memory-statistic[name="Processor"]'
```

## CPU Usage Statistics, Named IOSd Component

```
python ncc-establish-subscription.py --host=127.0.0.1 --port=2223 -u vagrant -p vagrant \
    --period=1000 \
    --xpath '/process-cpu-ios-xe-oper:cpu-usage/cpu-utilization/cpu-usage-processes/cpu-usage-process[pid=1][name="Chunk Manager"]'
```

