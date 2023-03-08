import pyomo.environ as pyomo       # Used to model the IP
import readAndWriteJson as rwJson   # Used for reading the data file in Json format
import matplotlib.pyplot as plt     # Used for plotting the result
import numpy as np

def readData(filename: str) -> dict:
    data = rwJson.readJsonFileToDictionary(filename)
    return data


def buildModel(data: dict) -> pyomo.ConcreteModel():
    #Definerer pyomo.ConcreteModel() som model for lettere anvendelse
    model = pyomo.ConcreteModel()

    #Parametrene defineres i modellen
    model.indkøbspris = data["var_cost"]
    model.opstillingspris = data["fixed_cost"]
    model.ventilhus = data["ventilhus"]
    model.produktionstid = data["produktionstid"]
    model.produkter = data["produkter"]
    model.efterspørgsel=data["demand"]
    model.r = data["r"]
    model.a=data["a"]
    model.K = data["var_cost"]
    model.kfm = data["var_cost"]
    model.kfs = data["var_cost"]
    model.ventilhus_længde = range(0, len(model.ventilhus))
    model.produkter_længde = range(0, len(model.produkter))
    model.delta=[model.efterspørgsel[v]*model.r[v] for v in range(0, len(model.efterspørgsel))]
    #model.delta=[data["demand"][i]*data["r"] for i in range(len(data["demand"]))] #sunes løsning er blevet replicated men med vores parameternavne

    #Variablerne bliver defineret i modellen
    model.x = pyomo.Var(model.ventilhus_længde, model.produkter_længde, within=pyomo.Binary)
    model.y = pyomo.Var(model.ventilhus_længde, within=pyomo.Binary)
    model.rho = pyomo.Var(model.ventilhus_længde, within=pyomo.NonNegativeReals)
    model.rho_constraint = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        model.rho_constraint.add(
            sum(model.delta[p] * model.x[v, p] for p in model.produkter_længde) == model.rho[v]
        )

    #Objektfunktionen tilføjes til modellen
    model.obj=pyomo.Objective(
        expr=sum(model.opstillingspris[v]*model.y[v] for v in model.ventilhus_længde)
             +sum(model.rho[v]*model.indkøbspris[v] for v in model.ventilhus_længde)
    )

    #Anden objektfunktion tilføjes til modellen
    #model.obj=pyomo.Objective(
    #    expr=sum(model.rho[v]*model.w[v]*model.kfm for v in model.ventilhus_længde)
    #         +sum(model.rho[v]*model.produktionstid[v]*model.K[v]*model.kfs[v] for v in model.ventilhus_længde)
    #)


    #Begræns brugen af ventilhuse så kun ventilhuse som passer til et produkt, kan tildeles til det produkt
    model.setcovering = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        for p in model.produkter_længde:
            model.setcovering.add(
                expr=model.x[v, p] <= model.a[v][p]
            )


    #Mindst en tildelt ventilhus til hvert produkt
    model.ventilhusdækning=pyomo.ConstraintList()
    for p in model.produkter_længde:
        model.ventilhusdækning.add(
            expr=(sum(model.x[v,p] for v in model.ventilhus_længde)>=1)
    )


    #Kun anvend ventilhuse som ses anvendt i modellen
    model.ventilhusanvendelse = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        for p in model.produkter_længde:
            model.ventilhusanvendelse.add(expr=model.x[v, p] <= model.y[v])




    return model


def solveModel(model: pyomo.ConcreteModel()):
    solver = pyomo.SolverFactory('gurobi')
    solver.solve(model, tee=True)




def displaySolution(model: pyomo.ConcreteModel(), data: dict):
    print('Solution value is:', pyomo.value(model.obj))

    for v in model.y:
        if pyomo.value(model.y[v])==1:
            print(f"Der skal anvendes {pyomo.value(model.rho[v])} enheder af ventilhus {model.y[v]}")


    print("")
    print('The following facilities are open:')
    for v in model.ventilhus_længde:
        if pyomo.value(model.y[v]) == 1:
            print(model.ventilhus[v], end=',')
    print('\nCustomers are covered as follows:')
    for p in model.produkter_længde:
        print(model.produkter[p],end=' ->\t')
        for v in model.ventilhus_længde:
            if model.a[v][p] == 1 and pyomo.value(model.y[v])==1:
                print(model.ventilhus[v], end=',')
        print('')

def main(filename: str):
    data = readData(filename)
    model = buildModel(data)
    solveModel(model)
    displaySolution(model, data)


if __name__ == '__main__':
    main("data")