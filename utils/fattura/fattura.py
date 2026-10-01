import xml.etree.ElementTree as ET
import xml.dom.minidom
import os, datetime

class Fattura():
    def __init__(self,
                template                = "template.xml",
                enterprise:  bool       = False,
                divisa     : str | None = None,
                prog_inv   : str        = None
                ):
        ET.register_namespace("p", "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2")
        self.module_dir    = os.path.dirname(__file__)
        self.template_path = os.path.join(self.module_dir, template)
        self.tree          = ET.parse(self.template_path)
        self.root          = self.tree.getroot()
        self.enterprise    = enterprise
        self.divisa        = divisa
        self.prog_inv      = prog_inv
        self.products      = []

    def add_info(self, 
                SSN        : str | None = None,
                via        : str | None = None,
                numero     : str | None = None,
                CAP        : str | None = None,
                comune     : str | None = None,
                nazione    : str | None = None
                ):
        self.SSN           = SSN
        self.address       = via
        self.number        = numero
        self.CAP           = CAP
        self.comune        = comune
        self.nation        = nazione

    def add_anagraph(self,
                    nome         : str = None,
                    cognome      : str = None,
                    nazione      : str = None,
                    codice       : str = None,
                    denom        : str = None
                    ): 

        if self.enterprise:
            self.country = nazione 
            self.code = codice
            self.denom = denom
        else:
            self.name = nome
            self.surname = cognome

    def add_product(self, amount: float, description: str, price: float, discount: float):
        self.products.append({
            "amount": amount,
            "description": description,
            "price": price,
            "discount": discount
        })

    def process(self):
        # ANAGRAFICA ---------------------------------
        header      = self.root.find("FatturaElettronicaHeader")
        trasmission = header.find("DatiTrasmissione")
        prog_inv    = trasmission.find("ProgressivoInvio")
        customer    = header.find("CessionarioCommittente")
        anagraf     = customer.find("DatiAnagrafici")

        ssn     = anagraf.find("CodiceFiscale")

        location = customer.find("Sede")
        address  = location.find("Indirizzo")
        number   = location.find("NumeroCivico")
        CAP      = location.find("CAP")
        city     = location.find("Comune")
        nation   = location.find("Nazione")

        if self.address: address.text   = self.address
        if self.number: number.text     = self.number
        if self.CAP: CAP.text           = self.CAP
        if self.comune: city.text       = self.comune
        if self.nation: nation.text     = self.nation
        if self.prog_inv: prog_inv.text = self.prog_inv
        if self.SSN: ssn.text           = self.SSN

        # AZIENDA / PRIVATO ------------------------

        if self.enterprise:
            name    = ET.Element("Denominazione")
            iva     = ET.Element("IdFiscaleIVA")
            country = ET.Element("IdPaese")
            code    = ET.Element("IdCodice")

            country.text = self.country
            code.text = self.code
            name.text = self.denom

            iva.append(country)
            iva.append(code)
            anagraf.insert(0, iva)
            anagraf.find("Anagrafica").append(name)
        else:
            name    = ET.Element("Nome")
            surname = ET.Element("Cognome")
            if self.name: name.text         = self.name
            if self.surname: surname.text   = self.surname
            anagraf.find("Anagrafica").append(name)
            anagraf.find("Anagrafica").append(surname)

        body = self.root.find("FatturaElettronicaBody")

        # PRODOTTI -----------------------------------
        products = body.find("DatiBeniServizi")
        total = 0
        for id, prod in enumerate(self.products):
            detail      = ET.Element("DettaglioLinee")

            line_num    = ET.Element("NumeroLinea")
            descr       = ET.Element("Descrizione")
            amount      = ET.Element("Quantita")
            um          = ET.Element("UnitaMisura")
            price       = ET.Element("PrezzoUnitario")
            total_price = ET.Element("PrezzoTotale")
            iva         = ET.Element("AliquotaIVA")

            line_num.text = str(id + 1)
            descr.text    = prod["description"]
            amount.text   = str(prod["amount"])
            um.text       = "PZ"

            # ScontoMaggiorazione solo se sconto > 0
            if float(prod["discount"]) > 0.0:
                sm = ET.Element("ScontoMaggiorazione")
                tipo = ET.Element("Tipo")
                tipo.text = "Sconto"
                percentuale = ET.Element("Percentuale")
                percentuale.text = str(prod["discount"])
                sm.append(tipo)
                sm.append(percentuale)
                detail.append(sm)

                prezzo_unitario_scontato = prod["price"] * (1 - float(prod["discount"]) / 100)
            else:
                prezzo_unitario_scontato = prod["price"]

            price.text = f"{prezzo_unitario_scontato:.2f}"
            total_price_prod = prod["amount"] * prezzo_unitario_scontato
            total_price.text = f"{total_price_prod:.2f}"
            iva.text = "22.00"
            total += total_price_prod

            detail.append(line_num)
            detail.append(descr)
            detail.append(amount)
            detail.append(um)
            detail.append(price)
            detail.append(total_price)
            detail.append(iva)

            products.insert(id, detail)

        # RIEPILOGO ---------------------------------
        riepilogo       = products.find("DatiRiepilogo")
        imponibile      = riepilogo.find("ImponibileImporto")
        imposta         = riepilogo.find("Imposta")
        iva             = riepilogo.find("AliquotaIVA")
        iva.text        = "22.00"
        imponibile.text = f"{total:.2f}"
        imposta.text    = f"{total / 100 * float(iva.text):.2f}"

        # PAGAMENTO --------------------------------
        pagamento   = body.find("DatiPagamento")
        dettagli    = pagamento.find("DettaglioPagamento")
        rif_termini = dettagli.find("DataRiferimentoTerminiPagamento")
        scadenza    = dettagli.find("DataScadenzaPagamento")
        importo     = dettagli.find("ImportoPagamento")

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        scadenza.text = rif_termini.text = today
        importo.text  = f"{float(imposta.text) + float(imponibile.text):.2f}"

        # DATI-GENERALI ------------------------------
        dati = body.find("DatiGenerali").find("DatiGeneraliDocumento")
        data = dati.find("Data")
        importo_tot = dati.find("ImportoTotaleDocumento")
        divisa = dati.find("Divisa")

        divisa.text = self.divisa
        data.text = today
        importo_tot.text = importo.text

    def XML_as_string(self):
        string = ET.tostring(self.root, encoding="utf-8").decode("utf-8")
        reparsed = xml.dom.minidom.parseString(string)
        pretty_xml = reparsed.toprettyxml(indent="    ")
        pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])
        return pretty_xml

    def save_file(self, name="fattura.xml"):
        with open(name, "w") as f:
            f.write(self.XML_as_string())
