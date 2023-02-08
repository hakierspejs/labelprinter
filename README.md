# labelprinter

This is a web service that allows the user to generate and print using Brother QL 800 label printer.

It allows the user to name an item and tell who is the owner.
When the label is printed, an entry to [gnujdb](https://g.hs-ldz.pl/) is also added and a QR code
pointing to it is included in the label.

In order to run it, execute:

```
sudo docker-compose up -d
```

This will expose it on port 5000. Before printing the label you should be able to see live preview.

## Technicalities

