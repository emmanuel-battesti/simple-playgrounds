import pymunk, pygame
from pygame.locals import K_q
from flatland.utils.config import *
from PIL import Image
import math, random

class Engine():

    def __init__(self, playground, agents, game_parameters):

        self.game_on = True
        self.agents = agents

        self.playground = playground

        self.playground.game_on = self.game_on

        self.agents_shape = {}

        for ag_name in self.agents:

            ag = self.agents[ag_name]['agent']

            self.playground.addAgent(ag)

            for anatomical_parts in ag.anatomy:

                part = ag.anatomy[anatomical_parts]

                if part.body is not None:
                    self.playground.space.add(part.body)

                if part.shape is not None:
                    self.playground.space.add(part.shape)

                if part.joint is not None:
                    for j in part.joint:
                        #self.playground.space.add(part.joint)
                        self.playground.space.add(j)

                self.agents_shape[part.shape] = ag

        self.handle_collisions()

        self.playground.initialize_textures()

        self.playground_img = None

        self.screen = pygame.display.set_mode((self.playground.width, self.playground.height))
        self.screen.set_alpha(None)

        # TODO: dd dictionary shape -> body id for fast identification during collisions

    def update_observations(self):

        img = self.playground.generate_playground_image_sensor()


        # For each agent, compute sensors
        for agent_name in self.agents:

            #TODO: for now, every sensor computed independently. But polar need only to be computed once
            self.agents[agent_name]['agent'].compute_sensors(img)

    def set_actions(self):

        for ag_name in self.agents:

            observations = self.agents[ag_name]['agent'].observations
            actions = self.agents[ag_name]['controller'].get_actions( )

            # Teerminate when q pressed
            if actions is None:
                self.game_on = False

            self.agents[ag_name]['agent'].apply_action(actions)

    def step(self):

        self.playground_img = None

        for ag in self.agents:
            self.agents[ag]['agent'].pre_step()

        for _ in range(SIMULATION_STEPS):
            self.playground.space.step(1. / SIMULATION_STEPS)

        if pygame.key.get_pressed()[K_q]:
            self.game_on = False

        self.playground.yielders_produce()

        self.playground.check_timers()

        # pygame.image.save(self.screen, 'imgs/'+str(self.ind_image).zfill(10)+'.png')
        # self.ind_image += 1

        # TODO: do all timers at once
        # TODO: Generlize, not just for doors
        #
        #
        # # TODO: update object state for timers and other states
        #
        #
        #
        # # TODO: update grasp only when grasp released
        # if self.agent.is_releasing == True:
        #
        #     self.is_holding = False
        #
        #     for link in self.grasped:
        #         self.space.remove(link)
        #     self.grasped = []

        # print(self.agent.reward, self.agent.health)


    def display_full_scene(self):

        img = self.playground.generate_playground_image()
        surf = pygame.surfarray.make_surface(img)
        self.screen.blit( surf , (0,0), None)

        pygame.display.flip()



    def agent_absorbs(self, arbiter, space, data):

        absorbable_shape = arbiter.shapes[1]
        agent_shape = arbiter.shapes[0]

        agent = self.agents_shape[agent_shape]

        absorbable_id = [id for id in self.playground.physical_entities if self.playground.physical_entities[id].shape_body == absorbable_shape][0]
        absorbable = self.playground.physical_entities[absorbable_id]

        reward = absorbable.reward

        self.playground.space.remove(absorbable.shape_body, absorbable.body_body)
        self.playground.physical_entities.pop(absorbable_id)
        if absorbable_id in self.playground.relations['basics']:
            self.playground.relations['basics'].remove(absorbable_id)

        # TODO: also if yielder

        for disp_id, disp_contain in self.playground.relations['yielders'].items():
            if absorbable_id in disp_contain:
                disp_contain.remove(absorbable_id)

        for disp_id, disp_contain in self.playground.relations['actionables']['dispensers'].items():
            if absorbable_id in disp_contain:
                disp_contain.remove(absorbable_id)


        # TODO: add reward and reset to zero at each ts
        agent.reward = reward
        agent.health += reward

        return True


    def agent_activates(self, arbiter, space, data):


        activable_shape = arbiter.shapes[1]

        agent_shape = arbiter.shapes[0]
        agent = self.agents_shape[agent_shape]

        is_activating = agent.is_activating

        all_activables =  list(self.playground.relations['actionables']['doors'].keys()) + list(self.playground.relations['actionables']['distractors']) + list(self.playground.relations['actionables']['dispensers'].keys())

        activable_id = [id for id in all_activables if self.playground.physical_entities[id].shape_sensor == activable_shape][0]
        activable = self.playground.physical_entities[activable_id]

        if is_activating:

            agent.is_activating = False



            if activable.actionable_type == 'dispenser':


                if len(self.playground.relations['actionables']['dispensers'][activable_id]) < activable.limit:
                    new_obj = activable.actionate()
                    id_new_object = self.playground.addEntity(new_obj, add_to_basics = False)
                    self.playground.relations['actionables']['dispensers'][activable_id].append(id_new_object)

            elif activable.actionable_type == 'door':

                if activable.door_closed:
                    activable.door_closed = False


                    door_id = self.playground.relations['actionables']['doors'][activable_id]
                    door = self.playground.physical_entities[door_id]

                    space.remove(door.body_body, door.shape_body)
                    door.visible = False

                    self.playground.timers[activable_id] = activable.time_open



            else:
                activable.actionate()

            print(self.playground.physical_entities)
            print(self.playground.relations)

        return True

    def agent_grasps(self, arbiter, space, data):

        agent_shape = arbiter.shapes[0]
        agent = self.agents_shape[agent_shape]

        is_grasping = agent.is_grasping

        activable_shape = arbiter.shapes[1]

        all_activables =  list(self.playground.relations['actionables']['graspables'])

        activable_id = [id for id in all_activables if self.playground.physical_entities[id].shape_sensor == activable_shape][0]
        activable = self.playground.physical_entities[activable_id]

        if is_grasping and (activable.movable == True) and (activable_id not in self.playground.grasped):

            # create new link
            self.is_grasping = False
            self.is_holding = True

            j1 = pymunk.PinJoint(activable.body_body, agent.anatomy['base'].body, (0,5), (0,-5))
            j2 = pymunk.PinJoint(activable.body_body, agent.anatomy['base'].body, (0,-5), (0,5))
            j3 = pymunk.PinJoint(activable.body_body, agent.anatomy['base'].body, (5,5), (0,5))
            j4 = pymunk.PinJoint(activable.body_body, agent.anatomy['base'].body, (5,-5), (0,5))

            self.playground.space.add(j1, j2, j3, j4)

            self.playground.grasped.append(j1)
            self.playground.grasped.append(j2)
            self.playground.grasped.append(j3)
            self.playground.grasped.append(j4)

        return True



    # TODO: norm PEP8, is_eating -> b_eating ?
    def agent_eats(self, arbiter, space, data):

        agent_shape = arbiter.shapes[0]
        agent = self.agents_shape[agent_shape]

        is_eating = agent.is_eating

        sensor_shape = arbiter.shapes[1]
        edible_id = [id for id in self.playground.relations['actionables']['edibles'] if self.playground.physical_entities[id].shape_sensor == sensor_shape][0]
        edible = self.playground.physical_entities[edible_id]

        if is_eating:

            agent.is_eating = False

            space.remove(edible.body_sensor, edible.shape_sensor)
            space.remove(edible.body_body, edible.shape_body)

            space.add_post_step_callback(self.eaten_shrinks, edible_id, agent )

        return True

    def eaten_shrinks(self, space, edible_id, agent):

        edible = self.playground.physical_entities[edible_id]
        edible.actionate()

        agent.reward += edible.reward

        if edible.radius > 5 :

            self.playground.space.add(edible.body_sensor, edible.shape_sensor)
            self.playground.space.add(edible.body_body, edible.shape_body)


        else:
            self.playground.physical_entities.pop(edible_id)
            self.playground.relations['actionables']['edibles'].remove(edible_id)

        return True

    def handle_collisions(self):

        # Collision handlers
        h_abs = self.playground.space.add_collision_handler(collision_types['agent'], collision_types['absorbable'])
        h_abs.pre_solve = self.agent_absorbs

        h_act = self.playground.space.add_collision_handler(collision_types['agent'], collision_types['activable'])
        h_act.pre_solve = self.agent_activates

        h_edible = self.playground.space.add_collision_handler(collision_types['agent'], collision_types['edible'])
        h_edible.pre_solve = self.agent_eats

        h_grasps = self.playground.space.add_collision_handler(collision_types['agent'], collision_types['graspable'])
        h_grasps.pre_solve = self.agent_grasps
