import pyomo.environ as pyomo       # Used to model the IP
import readAndWriteJson as rwJson   # Used for reading the data file in Json format


def readData(filename: str) -> dict:
    data = rwJson.readJsonFileToDictionary(filename)
    return data


def buildModel(data: dict) -> pyomo.ConcreteModel():
    #Definerer pyomo.ConcreteModel() som model for lettere anvendelse
    model = pyomo.ConcreteModel()

    #Parametrene defineres i modellen
    model.ventilhus = data["ventilhus"]
    model.produkter = data["produkter"]
    model.opstillingspris = data["fixed_cost"]
    model.indkøbspris=data["var_cost"]
    model.produktionstid = [data["produktionstid"][v]/60/60 for v in range(0, len(model.ventilhus))]
    model.efterspørgsel = data["demandvinter"]
    model.r = data["r"]
    model.delta=[model.efterspørgsel[v]*model.r[v] for v in range(0, len(model.efterspørgsel))]
    model.a=data["a2"]
    model.A=data["A"]
    model.w=[data["w"][v]/1000 for v in range(0, len(model.ventilhus))]
    model.K = data["K"]
    model.kfm = data["kfm"]
    model.kfs = data["kfsvinter"]/1000

    #No good inequality:
    model.YV1=data["Anvendteventilhuse"]
    model.C1=data["Anvendteventilhuseomvendt"]
    model.YV2=data["Anvendteventilhuse2"]
    model.C2=data["Anvendteventilhuseomvendt2"]
    model.YV3=data["Anvendteventilhuse3"]
    model.C3=data["Anvendteventilhuseomvendt3"]
    model.YV4=data["Anvendteventilhuse4"]
    model.C4=data["Anvendteventilhuseomvendt4"]
    model.YV5=data["Anvendteventilhuse5"]
    model.C5=data["Anvendteventilhuseomvendt5"]
    model.YV6=data["Anvendteventilhuse6"]
    model.C6=data["Anvendteventilhuseomvendt6"]
    model.YV7=data["Anvendteventilhuse7"]
    model.C7=data["Anvendteventilhuseomvendt7"]
    model.YV8=data["Anvendteventilhuse8"]
    model.C8=data["Anvendteventilhuseomvendt8"]

    #Parametre ved følsomhedsanalyse:
    #model.efterspørgsel=[round(data["demandsommer"][v]*0.6)for v in range(0, len(model.produkter))]
    #model.indkøbspris = [data["var_cost"][v]*0.6 for v in range(0, len(model.ventilhus))]
    #model.opstillingspris = [data["fixed_cost"][v]*0.6 for v in range(0, len(model.ventilhus))]
    #model.produktionstid = [data["produktionstid"][v]/60/60*0.6 for v in range(0, len(model.ventilhus))]

    #Længder:
    model.ventilhus_længde = range(0, len(model.ventilhus))
    model.produkter_længde = range(0, len(model.produkter))

    #Variablerne bliver defineret i modellen
    model.x = pyomo.Var(model.ventilhus_længde, model.produkter_længde, within=pyomo.Binary)
    model.y = pyomo.Var(model.ventilhus_længde, within=pyomo.Binary)
    model.rho = pyomo.Var(model.ventilhus_længde, within=pyomo.NonNegativeReals)
    model.rho_constraint = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        model.rho_constraint.add(
            sum(model.delta[p] * model.x[v, p] for p in model.produkter_længde) == model.rho[v]
        )

    #Minimering af omkostninger (1.)
    model.obj=pyomo.Objective(
        expr=sum(model.opstillingspris[v]*model.y[v] + model.rho[v]*model.indkøbspris[v] for v in model.ventilhus_længde)
    )

    #Minimering af CO2e udledninger (2.)
    #model.obj=pyomo.Objective(
    #    expr=sum(model.rho[v]*model.w[v]*model.kfm + model.rho[v]*model.produktionstid[v]*model.K*model.kfs for v in model.ventilhus_længde)
    #)

    #Minimering af omkostninger inkl. CO2 afgifter (3.)
    #model.obj=pyomo.Objective(
    #    expr=sum(model.opstillingspris[v]*model.y[v] + model.rho[v]*model.indkøbspris[v] for v in model.ventilhus_længde)
    #         +(sum(model.rho[v]*model.w[v]*model.kfm + model.rho[v]*model.produktionstid[v]*model.K*model.kfs for v in model.ventilhus_længde))*model.A
    #)

    #No good inequality objektfunktion. (4.)
    #model.obj=pyomo.Objective(
    #    expr=sum(model.opstillingspris[v]*model.y[v] + model.rho[v]*model.indkøbspris[v] + model.rho[v]*model.w[v]*model.kfm + model.rho[v]*model.produktionstid[v]*model.K*model.kfs for v in model.ventilhus_længde)
    #)

    #Begræns brugen af ventilhuse så kun ventilhuse som passer til et produkt, kan tildeles til det produkt
    #Begrænsningen tager ikke højde for, at hvis der ikke er efterspørgsel så skal et produkt ikke dækkes.
    model.setcovering = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        for p in model.produkter_længde:
            if model.efterspørgsel[p] > 0:
                model.setcovering.add(
                    expr=model.x[v, p] <= model.a[v][p]
                )


    #Mindst en tildelt ventilhus til hvert produkt
    model.ventilhusdækning=pyomo.ConstraintList()
    for p in model.produkter_længde:
        model.ventilhusdækning.add(
            expr=(sum(model.x[v,p] for v in model.ventilhus_længde)==1)
    )


    #Kun anvend ventilhuse som ses anvendt i modellen
    model.ventilhusanvendelse = pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        for p in model.produkter_længde:
            model.ventilhusanvendelse.add(expr=model.x[v, p] <= model.y[v])

    #Kontrol af åbning af ventilhustyper (sekundær objektfunktion)
    model.ventilhus2=pyomo.ConstraintList()
    for v in model.ventilhus_længde:
        model.ventilhus2.add(expr=model.rho[v]>=model.y[v])

    #No good inequality - accumulated constraints
    #model.nogoodinequality1=pyomo.Constraint(expr=(sum(model.C1[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV1[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality2=pyomo.Constraint(expr=(sum(model.C2[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV2[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality3=pyomo.Constraint(expr=(sum(model.C3[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV3[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality4=pyomo.Constraint(expr=(sum(model.C4[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV4[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality5=pyomo.Constraint(expr=(sum(model.C5[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV5[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality6=pyomo.Constraint(expr=(sum(model.C6[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV6[v] for v in model.ventilhus_længde)))
    #model.nogoodinequality7=pyomo.Constraint(expr=(sum(model.C7[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV7[v] for v in model.ventilhus_længde)))
    #INFEASIBLE: model.nogoodinequality8=pyomo.Constraint(expr=(sum(model.C8[v]*model.y[v] for v in model.ventilhus_længde))>=1-(sum(model.YV8[v] for v in model.ventilhus_længde)))


    #Epsilon constraint til løsning af bikriterie problem.
    #model.epsilonconstraint=pyomo.ConstraintList()
    #model.epsilonconstraint.add(expr=(sum(model.rho[v]*model.w[v]*model.kfm for v in model.ventilhus_længde)
    #                                 +sum(model.rho[v]*model.produktionstid[v]*model.K*model.kfs for v in model.ventilhus_længde))<=617.64)

    return model



def solveModel(model: pyomo.ConcreteModel()):
    solver = pyomo.SolverFactory('gurobi')
    solver.solve(model, tee=True)




def displaySolution(model: pyomo.ConcreteModel(), data: dict):
    print('Solution value is:', pyomo.value(model.obj))

    print("CO2e Udslip i kg")
    print(sum(pyomo.value(model.rho[v])*model.w[v]*model.kfm for v in model.ventilhus_længde)
             +sum(pyomo.value(model.rho[v])*model.produktionstid[v]*model.K*model.kfs for v in model.ventilhus_længde))
    print("")
    print("Omkostninger i kr")
    print(sum(model.opstillingspris[v]*pyomo.value(model.y[v]) for v in model.ventilhus_længde)
             +sum(pyomo.value(model.rho[v])*model.indkøbspris[v] for v in model.ventilhus_længde))

    for v in model.y:
        if pyomo.value(model.y[v])==1:
            print(f"Der skal anvendes {pyomo.value(model.rho[v])} enheder af ventilhus {model.y[v]}")

    print('Solution value is:', pyomo.value(model.obj))
    print(f"Der indkøbes i alt {sum(pyomo.value(model.rho[v]) for v in model.ventilhus_længde)}")
    print("")
    print('Følgende ventilhuse bliver anvendt i løsningen:')
    for v in model.ventilhus_længde:
        if pyomo.value(model.y[v]) == 1:
            print(model.ventilhus[v], end=', ')
    print("")
    print('\nProdukterne er dækket som følgende:')
    for p in model.produkter_længde:
        print(model.produkter[p],end=' ->\t')
        for v in model.ventilhus_længde:
            if model.a[v][p] == 1 and pyomo.value(model.x[v,p])==1:
                if pyomo.value(model.rho[v])>0:
                    print(model.ventilhus[v], end=',')
                else:
                    print("intet ventilhus allokeret")
        print('')

def main(filename: str):
    data = readData(filename)
    model = buildModel(data)
    solveModel(model)
    displaySolution(model, data)


if __name__ == '__main__':
    main("data")