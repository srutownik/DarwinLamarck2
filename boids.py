import numpy as np
import mesa
import random


def limit(val, low=0, high=1000):
    return max(low, min(high, val))

def score_agent_hunger(agent):
    return limit((agent.MAX_ENERGY - agent.energy) * agent.hunger_a + agent.hunger_b)

def filter_by_type(population, agentType):
    return (agent for agent in population if type(agent) is agentType)

def closes_neighbour(agent, population):
    def distance_from_agent(neighbour):
        return agent.space.get_distance(agent.pos, neighbour.pos)
    return min((neighbour for neighbour in population),
               key=distance_from_agent,
               default=agent)  

def avoidance_score(agent, neighbours):
    closest = closes_neighbour(agent, neighbours)
    distance_to_closest = agent.space.get_distance(agent.pos, closest.pos)
    return 1 - (distance_to_closest / agent.VIEW_RANGE)

def avoid(neighbour_heading, radius):
    length = np.linalg.norm(neighbour_heading)
    return neighbour_heading * (radius - length) / length

def escape(agent, neighbours):
    return sum((avoid(agent.space.get_heading(agent.pos, neighbour.pos),
                      agent.VIEW_RANGE)
                for neighbour in neighbours),
               np.array([0, 0]))

def cohere(agent, neighbours):
    v = sum((agent.space.get_heading(agent.pos, neighbour.pos)
             for neighbour in neighbours))
    return v / np.linalg.norm(v)

def align(agent, neighbours):
    return np.mean(np.array([agent.space.get_heading(agent.pos, neighbour.pos)
                             for neighbour in neighbours]))

def couple(agent, population):
    population = list(population)
    if not population:
        return np.array([0, 0])

    cohersion  = cohere(agent, population)
    alignment  = align(agent, population)
    separation = escape(agent, (neighbour
                                for neighbour in population
                                if agent.space.get_distance(agent.pos, neighbour.pos) <= agent.VIEW_RANGE / 2))
    return cohersion + separation + alignment

class Grass:
    RADIUS = 6e-4
    energy = 0

    def step(self):
        pass
    
    def advance(self):
        pass

class Decision:
    def __init__(self, pos, cost=1):
        self.pos  = pos
        self.cost = cost

class Agent:
    VIEW_RANGE = 0.1
    MAX_ENERGY = 200
    RADIUS = None

    def __init__(self, space : mesa.space.ContinuousSpace):
        self.space = space
        self.energy = self.MAX_ENERGY
        self.pos = None
        
    def step(self):
        neighbours = self.space.get_neighbors(self.pos, self.VIEW_RANGE, include_center=False)
        self.decision = self.make_deicision(neighbours)
    
    def advance(self):
        if self.valid_decision():
            self.move()
        self.energy -= self.decision.cost
        if self.energy < self.MAX_ENERGY:
            self.find_food()
        self.penalty()
        if self.energy < 0:
            self.space._remove_agent(self.pos, self)

    def move(self):
        self.space.move_agent(self, self.decision.pos)
    
    def valid_decision(self):
        return not self.space.get_neighbors(self.decision.pos, self.RADIUS)

    def make_deicision(self, neighbours):
        decisions, weights = self.get_weighted_decisions(neighbours)
        decision = random.choices(decisions, weights)[0](neighbours)
        decision.pos = self.space.torus_adj(decision.pos)
        return decision
    
    def find_food(self):
        pass

    def penalty(self):
        pass

    def get_weighted_decisions(self, neighbours):
        pass

class SheepAgent(Agent):
    RADIUS = 1e-3

    def __init__(self, genes, space):
        super(SheepAgent, self).__init__(space)
        self.apply_genes(genes)

    def apply_genes(self, genes):
        (  self.hunger_a,   self.hunger_b,
             self.fear_a,     self.fear_b, self.fear_speed,
         self.coupling_a, self.coupling_b                 ) = genes

    def extract_genes(self):
        return (  self.hunger_a,   self.hunger_b,
                    self.fear_a,     self.fear_b, self.fear_speed,
                self.coupling_a, self.coupling_b                 )

    def hunger(self, neighbours):
        food = filter_by_type(neighbours, Grass)
        closest = closes_neighbour(self, food)
        return Decision(self.space.get_heading(self.pos, closest.pos))

    def coupling(self, neighbours):
        sheep = filter_by_type(neighbours, SheepAgent)
        return Decision(couple(self, sheep))

    def fear(self, neighbours):
        return Decision(escape(self, neighbours), 1 + self.fear_speed * 2 / 1000)

    def score_hunger(self):
        return score_agent_hunger(self)

    def score_coupling(self, neighbours):
        sheep = filter_by_type(neighbours, SheepAgent)
        return avoidance_score(self, sheep)

    def score_fear(self, neighbours):
        wolves = filter_by_type(neighbours, WolfAgent)
        return avoidance_score(self, wolves)

    def get_weighted_decisions(self, ns):
        return ([self.hunger,         self.coupling,           self.fear],
                [self.score_hunger(), self.score_coupling(ns), self.score_fear(ns)])

class WolfAgent(Agent):
    RADIUS = 1.4e-2

    def __init__(self, genes, space):
        super(WolfAgent, self).__init__(space)
        self.apply_genes(genes)

    def apply_genes(self, genes):
        (  self.hunger_a,   self.hunger_b, self.hunger_speed,
         self.coupling_a, self.coupling_b                   ) = genes

    def extract_genes(self):
        return (  self.hunger_a,   self.hunger_b, self.hunger_speed,
                self.coupling_a, self.coupling_b                   )

    def hunger(self, neighbours):
        food = filter_by_type(neighbours, SheepAgent)
        closest = closes_neighbour(self, food)
        return Decision(self.space.get_heading(self.pos, closest.pos), cost=1 + self.hunger_speed * 2 / 1000)

    def coupling(self, neighbours):
        wolves = filter_by_type(neighbours, WolfAgent)
        return Decision(couple(self, wolves))

    def score_hunger(self):
        return score_agent_hunger(self)

    def score_coupling(self, neighbours):
        wolves = filter_by_type(neighbours, WolfAgent)
        return avoidance_score(self, wolves)

    def get_weighted_decisions(self, ns):
        return ([self.hunger,         self.coupling],
                [self.score_hunger(), self.score_coupling(ns)])