import strawberry
from strawberry.fastapi import GraphQLRouter

from bff.interfaces.graphql.consultas import Query
from bff.interfaces.graphql.mutaciones import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_router = GraphQLRouter(schema, path="/graphql")
